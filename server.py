#!/usr/local/bin/python3

import math
import os

import feedparser
import flask
from flask import Flask, jsonify, Response
from flask import request
from dateutil import parser
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

PAGE_SIZE = 10

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
db = SQLAlchemy(app)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    url = db.Column(db.String(1024), nullable=False, unique=True)

    def __repr__(self):
        return '<Feed ' + self.title + ': ' + self.url + '>'


class FeedItem(db.Model):
    url = db.Column(db.String(1024), primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(2048), nullable=False)
    time = db.Column(db.String(256), nullable=False)
    parsed_time = db.Column(db.DateTime(), nullable=True)

    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)

    def __repr__(self):
        return '<FeedItem in feed ' + self.feed.title + ' with name' + self.title + ': ' + self.url + '>'


def get_feed_html_page_data(feed_id, page):
    feed = Feed.query.get(feed_id)
    # if feed_id < 0 or feed_id >= len(added_rss):
    #     print("feed_id out of range")
    #     return None

    items = FeedItem.query.filter(FeedItem.feed_id == feed_id).all()
    page_count = max(math.ceil(len(items) / PAGE_SIZE), 1)
    if page > page_count:
        print("page out of range")
        return None, None, None

    info = {
        "page_count": page_count,
        "active_page": page,
        "articles_count": len(items)
    }

    start_index = (page - 1) * PAGE_SIZE
    end_index = min(page * PAGE_SIZE, len(items))

    return feed, info, items[start_index:end_index]


def parse_feed_from_url(rss_feed_link):
    d = feedparser.parse(rss_feed_link)

    def rss_entry_to_feed_item(entry):
        published = entry.published
        published_parsed = parser.parse(published)

        return FeedItem(url=entry.link,
                        title=entry.title,
                        time=published,
                        parsed_time=published_parsed,
                        description=entry.description)

    feed = Feed(title=d.feed.title, url=rss_feed_link)
    feed.items = [rss_entry_to_feed_item(entry) for entry in d.entries]
    for i in feed.items:
        i.feed_id = feed.id
    return feed


def reload_feed(feed_id):
    feed_url = Feed.query.get(feed_id).url
    new_feed = parse_feed_from_url(feed_url)
    new_items = [i for i in new_feed.items if FeedItem.query.get(i.url) is None]
    if len(new_items) == 0:
        pass
    for item in new_items:
        item.feed_id = feed_id
        db.session.add(item)
    db.session.commit()


def add_rss_feed_link(rss_feed_link):
    feed = parse_feed_from_url(rss_feed_link)
    try:
        db.session.add(feed)
        db.session.commit()
        return True
    except IntegrityError:
        return False


def get_feeds():
    return Feed.query.all()


@app.route('/', methods=["GET"])
def root():
    return flask.redirect('/feed', code=302)


@app.route('/feed', methods=["GET"])
@app.route('/feed/<int:feed_id>', methods=["GET"])
@app.route('/feed/<int:feed_id>/<int:page>', methods=["GET"])
def feed(feed_id=None, page=1):
    if feed_id is None:
        data = {"no_feeds": True, "items": []}
        info = None
        items = []
    else:
        data, info, items = get_feed_html_page_data(feed_id, page)
        if data is None:
            return flask.abort(400)
        info["no_feeds"] = False
    feeds = get_feeds()
    return flask.render_template('index.html', data=data, items=items, feeds=feeds, info=info)


@app.route('/feed', methods=["POST"])
def add_rss():
    rss_feed_link = request.json['rss-feed-link']
    add_status = add_rss_feed_link(rss_feed_link)
    if add_status:
        return flask.redirect("/")
    else:
        status_code = flask.Response(status=208)
        return status_code


@app.route('/feedupdate/<int:feed_id>', methods=["GET"])
def feed_update(feed_id):
    reload_feed(feed_id)
    return flask.redirect("/feed/" + str(feed_id), code=302)
