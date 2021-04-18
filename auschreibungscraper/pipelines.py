# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import dataset
# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

from .items import Attachments, Message, PublicatingEntity, Publication


# TODO: To PATCH-style upserts instead of inserts
class AuschreibungscraperPipeline:

    def open_spider(self, spider):
        self.db = dataset.connect("sqlite:///test.db")
        self.msg_table = self.db['message']
        self.publication_table = self.db['publication']
        self.publicating_entity = self.db['publicating_entity']
        self.attachment_table = self.db['attachment']

    def _process_message(self, item):
        try:
            self.msg_table.insert(item, types={"data": self.db.types.json, "files": self.db.types.json, "file_urls": self.db.types.json})
        except:
            import pdb;pdb.set_trace()

    def _process_attachment(self, item):
        try:
            self.attachment_table.insert(item, types={"raw": self.db.types.json, "file_urls":self.db.types.json, "files": self.db.types.json})
        except:
            import pdb;pdb.set_trace()

    def _process_publication(self, item):
        try:
            self.publication_table.insert(item, types={"data":self.db.types.json, "attachments": self.db.types.json, "messages": self.db.types.json})
        except:
            import pdb;pdb.set_trace()

    def _process_publicating_entity(self, item):
        try:
            self.publicating_entity.insert(item)
        except:
            import pdb;pdb.set_trace()

    def process_item(self, item, spider):
        if isinstance(item, Attachments):
            self._process_attachment(item)
        elif isinstance(item, Message):
            self._process_message(item)
        elif isinstance(item, Publication):
            self._process_publication(item)
        elif isinstance(item, PublicatingEntity):
            self._process_publicating_entity(item)
        else:
            raise NotImplementedError(f"unknown entity: {type(item)}")

        return item
