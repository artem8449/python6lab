import math
import feedparser
from dateutil import parser
from sqlalchemy.exc import IntegrityError

import server

PAGE_SIZE = 10


class Feed(server.db.Model):
    id = server.db.Column(server.db.Integer, primary_key=True)
    title = server.db.Column(server.db.String(256), nullable=False)
    url = server.db.Column(server.db.String(1024), nullable=False, unique=True)

    def __repr__(self):
        return 'Feed ' + self.title + ': ' + self.url


class FeedItem(server.db.Model):
    url = server.db.Column(server.db.String(1024), primary_key=True)
    title = server.db.Column(server.db.String(256), nullable=False)
    description = server.db.Column(server.db.String(2048), nullable=False)
    time = server.db.Column(server.db.String(256), nullable=False)
    parsed_time = server.db.Column(server.db.DateTime(), nullable=True)

    feed_id = server.db.Column(server.db.Integer, server.db.ForeignKey('feed.id'), nullable=False)

    def __repr__(self):
        return 'Article ' + self.title + ': ' + self.url


def get_page_of_articles(feed_id, current_page):
    feed = Feed.query.get(feed_id)

    items = FeedItem.query.filter(FeedItem.feed_id == feed_id).order_by(FeedItem.parsed_time.desc()).all()
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
        server.db.session.add(item)
    server.db.session.commit()


def add_new_feed(feed_link):
    feed = parse_feed(feed_link)
    try:
        server.db.session.add(feed)
        server.db.session.commit()
        return True
    except IntegrityError:
        return False


def get_all_feeds():
    return Feed.query.all()
