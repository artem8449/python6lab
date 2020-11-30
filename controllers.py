import flask
from flask import request

from logic import get_all_feeds, get_page_of_articles, add_new_feed, reload_feed
from server import app


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
