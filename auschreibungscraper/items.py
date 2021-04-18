# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class Message(scrapy.Item):
    oid = scrapy.Field()
    date = scrapy.Field()
    title = scrapy.Field()
    body = scrapy.Field()
    publication_id = scrapy.Field()
    data = scrapy.Field()
    file_name = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()

class Attachments(scrapy.Item):
    oid = scrapy.Field()
    name = scrapy.Field()
    file_urls = scrapy.Field()
    files = scrapy.Field()
    raw = scrapy.Field()
    # TODO: Tree

class PublicatingEntity(scrapy.Item):
    name = scrapy.Field()

class Publication(scrapy.Item):
    oid = scrapy.Field()
    title = scrapy.Field()
    publicated_by = scrapy.Field()
    data = scrapy.Field()
    attachments = scrapy.Field()
    messages = scrapy.Field()
