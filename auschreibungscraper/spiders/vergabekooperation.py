import urllib.parse

import html_text
import scrapy

from ..items import Attachments, Message, PublicatingEntity, Publication


class VergabekooperationSpider(scrapy.Spider):
    name = "vergabekooperation"
    allowed_domains = ["vergabekooperation.berlin"]

    th_contexts = ["preinformations", "publications", "awardPublications"]
    start_urls = [
        "https://vergabekooperation.berlin/NetServer/PublicationSearchControllerServlet?Max=10000&function=SearchPublications&Gesetzesgrundlage=All&Category=PriorInformation&thContext=preinformations",
        "https://vergabekooperation.berlin/NetServer/PublicationSearchControllerServlet?Max=10000&function=SearchPublications&Gesetzesgrundlage=All&Category=InvitationToTender&thContext=publications",
        "https://vergabekooperation.berlin/NetServer/PublicationSearchControllerServlet?Max=10000&function=SearchPublications&Gesetzesgrundlage=All&Category=ContractAward&thContext=awardPublications",
    ]

    def parse(self, response):
        for publication in response.css(".publicationDetail"):
            oid = publication.xpath("@data-oid").get()
            category = publication.xpath("@data-category").get()
            yield response.follow(
                f"https://vergabekooperation.berlin/NetServer/PublicationControllerServlet?function=Detail&TOID={oid}&Category={category}",
                callback=self.parse_detail,
                meta={"oid":oid}
            )

    def parse_detail(self, response):

        publication_tables = response.css(".tableContractNotice")
        publication_data = {
            None: {}
        }
        for publication_table in publication_tables:
            publication_section = publication_table.css(".color-main::text").get()
            if not publication_section in publication_data:
                publication_data[publication_section] = {}
            for row in publication_table.css("tr:not(.tableNoticeHead)"):
                row_tds = [html_text.extract_text(x) for x in row.css("td").getall()]
                if len(row_tds) != 2:
                    continue

                k, v = row_tds
                publication_data[publication_section][k] = v

        download_path = response.css(".downloadDocuments").css("a").xpath("@href").get()
        if download_path:
            download_url = response.urljoin(download_path)
            yield response.follow(
                download_url,
                callback=self.parse_detail_2,
                meta={"cookiejar": download_path, "oid": response.meta['oid']},
            )
            publication_data[None]["attachment_download_url"] = download_url

        publication = Publication(
            oid=response.meta['oid'],
            # TODO: title=response.meta['title'],
            # TODO: publicated_by=response.meta['publicated_by'],
            # TODO: attachments, messages
            data = publication_data,
            )
        yield publication

    def parse_detail_2(self, response):
        cookiejar = response.meta["cookiejar"]
        data = {
            "attachment_versions": [],
            "messages": [],
            "__type": "Attachment_Messages",
        }
        for download_version in response.css(".zipFileContents"):
            oid = download_version.xpath("@data-oid").get()
            token = download_version.xpath("@data-token").get()
            version = download_version.xpath("./parent::*/parent::*/td[1]/text()").get()
            date = download_version.xpath("./parent::*/parent::*/td[2]/text()").get()
            data["attachment_versions"].append(
                {"oid": oid, "version": version, "date": date}
            )
            yield scrapy.http.FormRequest(
                "https://vergabekooperation.berlin/NetServer/DataProvider",
                formdata={"param": "FileTree", "oid": oid, "VALIDATION_TOKEN": token},
                meta={"documentOID": response.meta['oid'], "oid":oid, "respon": response, "cookiejar": cookiejar},
                callback=self.parse_dataprovider_filetree,
            )

        for message in response.css(".publicMessage"):
            oid = message.xpath("@data-oid").get()
            row_tds = [
                html_text.extract_text(x)
                for x in message.xpath("./parent::*/parent::*").css("td").getall()
            ]
            _, _, date, title = row_tds
            data["messages"].append({"oid": oid, "date": date, "title": title})
            yield scrapy.http.FormRequest(
                "https://vergabekooperation.berlin/NetServer/DataProvider",
                formdata={"param": "PublicMessageDetail", "oid": oid},
                meta={"documentOID": response.meta['oid'], "messageOID": oid},
                callback=self.parse_dataprovider_publicmessagedetail,
            )

        yield Publication(oid=response.meta['oid'], attachments=data['attachment_versions'], messages=data['messages'])

    def _parse_filetree_section(self, doc_oid, json):
        file_urls = []
        for name, file in json.items():
            # This is how they to it in production m)
            if 'fileName' in file:
                url = f"https://vergabekooperation.berlin/NetServer/TenderingProcedureDetails?function=_DownloadTenderDocument&documentOID={doc_oid}&Document={file['encodedName']}"
                file_urls.append(url)
            else:
                file_urls += self._parse_filetree_section(doc_oid, file)
        # for section_name, section in response_json.items():
        #     for idx, file in section.items():
        #         print(file)
        #         url = f"https://vergabekooperation.berlin/NetServer/TenderingProcedureDetails?function=_DownloadTenderDocument&documentOID={}&Document={file['encodedName']}"
        #         file_urls.append(url)
        return file_urls

    def parse_dataprovider_filetree(self, response):
        # cookiejar = response.meta['cookiejar']
        if not response.text:
            import pdb; pdb.set_trace()
        # print("Response Text", response.text)
        response_json = response.json()
        file_urls = []
        file_urls = self._parse_filetree_section(response.meta['documentOID'], response_json)
        return Attachments(oid=response.meta['oid'], file_urls=file_urls, raw=response_json)
        # yield {"FileTree": response_json, "file_urls": file_urls, "__type": "FileTree"}

    def parse_dataprovider_publicmessagedetail(self, response):
        # TODO
        # print(self, response.text)
        response_json = response.json()
        msg = Message(
            oid = response.meta['messageOID'],
            date=response_json["time"],  # TODO: Parse
            title=response_json["subject"],
            body=response_json["body"],
            publication_id=response_json["tenderOID"],
            data={
                "authorityKey": response_json["authorityKey"],
                "tender": response_json["tender"],
            },
        )
        if "attachmentLink" in response_json:
            msg['file_name']=response_json["fileName"]
            msg['file_urls']=[response.urljoin(response_json["attachmentLink"])]

        return msg

    def parse_downloaded_file(self, response):
        with open(f"{response.meta['filename']}", "wb") as f:
            f.write(response.body)
