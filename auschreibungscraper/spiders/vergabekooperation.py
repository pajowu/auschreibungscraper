import urllib.parse

import html_text
import scrapy


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
            )

    def parse_detail(self, response):
        download_path = response.css(".downloadDocuments").css("a").xpath("@href").get()
        download_url = response.urljoin(download_path)
        yield response.follow(download_url, callback=self.parse_detail_2, meta={'cookiejar': download_path})

        publication_tables = response.css(".tableContractNotice")
        publication_data = {None: {"attachment_download_url": download_url}, "__type": "Detail"}
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

        yield publication_data

    def parse_detail_2(self, response):
        cookiejar = response.meta['cookiejar']
        data = {"attachment_versions": [], "messages": [], "__type": "Attachement_Messages"}
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
                meta={"documentOID": oid, "respon": response, "cookiejar": cookiejar},
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
                meta={"documentOID": oid},
                callback=self.parse_dataprovider_publicmessagedetail,
            )

    def parse_dataprovider_filetree(self, response):
        # cookiejar = response.meta['cookiejar']
        if not response.text:
            import pdb;pdb.set_trace()
        print("Response Text", response.text)
        response_json = response.json()
        file_urls = []
        for section_name, section in response_json.items():
            for idx, file in section.items():
                url = f"https://vergabekooperation.berlin/NetServer/TenderingProcedureDetails?function=_DownloadTenderDocument&documentOID={response.meta['documentOID']}&Document={file['encodedName']}"
                file_urls.append(url)
        yield {"FileTree": response_json, "file_urls": file_urls, "__type": "FileTree"}

    def parse_dataprovider_publicmessagedetail(self, response):
        # TODO
        print(self, response.text)

    def parse_downloaded_file(self, response):
        with open(f"{response.meta['filename']}", "wb") as f:
            f.write(response.body)
