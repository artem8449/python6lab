#!/usr/local/bin/python3

import math
import os

import feedparser
import flask
from flask import Flask
from flask import request
from dateutil import parser
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
db = SQLAlchemy(app)

PAGE_SIZE = 10


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    url = db.Column(db.String(1024), nullable=False, unique=True)

    def __repr__(self):
        return 'Feed ' + self.title + ': ' + self.url


class FeedItem(db.Model):
    url = db.Column(db.String(1024), primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(2048), nullable=False)
    time = db.Column(db.String(256), nullable=False)
    parsed_time = db.Column(db.DateTime(), nullable=True)

    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)

    def __repr__(self):
        return 'Article ' + self.title + ': ' + self.url


def get_page_of_articles(feed_id, current_page):
    feed = Feed.query.get(feed_id)

    items = FeedItem.query.filter(FeedItem.feed_id == feed_id).all()
    page_count = max(1, math.ceil(len(items) / PAGE_SIZE))
    if current_page > page_count:
        print("requested page does not exist")
        return None, None, None

    info = {
        "no_feeds": False,
        "current_page": current_page,
        "page_count": page_count,
        "articles_count": len(items)
    }

    start_index = (current_page - 1) * PAGE_SIZE
    end_index = min(len(items), current_page * PAGE_SIZE)

    return feed, info, items[start_index:end_index]


def parse_feed(feed_link):
    feed_dict = feedparser.parse(feed_link)

    feed = Feed(title=feed_dict.feed.title, url=feed_link)

    def feed_item_from_rss_entry(entry):
        return FeedItem(url=entry.link,
                        title=entry.title,
                        time=entry.published,
                        parsed_time=parser.parse(entry.published),
                        description=entry.description)

    feed.items = [feed_item_from_rss_entry(entry) for entry in feed_dict.entries]

    for item in feed.items:
        item.feed_id = feed.id

    return feed


def reload_feed(feed_id):
    feed_url = Feed.query.get(feed_id).url
    feed = parse_feed(feed_url)
    new_items = [item for item in feed.items if FeedItem.query.get(item.url) is None]
    for item in new_items:
        item.feed_id = feed_id
        db.session.add(item)
    db.session.commit()


def add_new_feed(feed_link):
    feed = parse_feed(feed_link)
    try:
        db.session.add(feed)
        db.session.commit()
        return True
    except IntegrityError:
        return False


def get_all_feeds():
    return Feed.query.all()


@app.route('/', methods=["GET"])
def root():
    return flask.redirect('/feed', code=302)


@app.route('/feed', methods=["GET"])
@app.route('/feed/<int:feed_id>', methods=["GET"])
@app.route('/feed/<int:feed_id>/<int:page>', methods=["GET"])
def show_feed(feed_id=None, page=1):
    if feed_id is None:
        selected_feed = None
        info = {"no_feeds": True}
        items = []
    else:
        selected_feed, info, items = get_page_of_articles(feed_id, page)
        if selected_feed is None:
            return flask.abort(400)
    all_feeds = get_all_feeds()
    return flask.render_template('index.html', selected_feed=selected_feed, items=items, all_feeds=all_feeds, info=info)


@app.route('/feed', methods=["POST"])
def add_rss():
    rss_feed_link = request.json['rss-feed-link']
    add_status = add_new_feed(rss_feed_link)
    if add_status:
        status_code = flask.Response(status=302)
        return status_code
    else:
        status_code = flask.Response(status=208)
        return status_code


@app.route('/feed_update/<int:feed_id>', methods=["GET"])
def feed_update(feed_id):
    reload_feed(feed_id)
    return flask.redirect("/feed/" + str(feed_id), code=302)
