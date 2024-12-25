#!/usr/bin/env python3

# %% import library
import argparse
import mwclient
import pandas
import csv
import json

# %% define functions


# %% define class.42.3"


class mw_connection:
    def __init__(self, user, password):
        self.user_agent = "wikinova_tools/0.1 (ward.chris.s@gmail.com)"
        self.site = mwclient.Site(
            "wikinova.chriswardlab.com", clients_useragent=self.user_agent, path="/"
        )
        self.site.login(username=user, password=password)

        print("hello - connection to wiki is established")

        self.prepare_book_catalogue_fields()

    def prepare_book_catalogue_fields(self):
        self.bc_fields = [
            "_id",
            "author_details",
            "title",
            "isbn",
            "publisher",
            "date_published",
            "rating",
            "bookshelf_id",
            "bookshelf",
            "read",
            "series_details",
            "pages",
            "notes",
            "list_price",
            "anthology",
            "location",
            "read_start",
            "read_end",
            "format",
            "signed",
            "loaned_to",
            "anthology_titles",
            "description",
            "genre",
            "language",
            "date_added",
            "goodreads_book_id",
            "last_goodreads_sync_date",
            "last_update_date",
            "book_uuid",
        ]

    def pull_books_to_csv(self, output_path=None):
        # get entries in the "Library" category that lists the books
        library = self.site.categories["Library"]
        book_list = [
            t.text() for t in library if t.name != "Template for adding new books"
        ]

        book_dict = {}
        for b in book_list:
            book_info = b.split("\n......END OF RECORD......")[0]
            entry_list = ("\n" + book_info).split("\n== ")
            entry_dict = {}
            for e in entry_list:
                k = e.split(" ==\n")[0]
                if len(e.split(" ==\n")) > 1:
                    v = e.split(" ==\n")[1]
                else:
                    v = ""
                entry_dict[k] = v.strip()
            entry_dict["_id"] = None
            if entry_dict["isbn"] in book_dict:
                print(entry_dict["title"])
                print(f"warning - duplicate isbn observed [{entry_dict['isbn']}]")
            book_dict[entry_dict["isbn"]] = entry_dict

        with open(output_path, "w", encoding="utf-8", newline="") as openfile:
            csvwriter = csv.writer(openfile)

            csvwriter.writerow(self.bc_fields)

            for isbn, values in book_dict.items():
                row = []
                for k in self.bc_fields:
                    try:
                        row.append(values[k])
                    except:
                        print(f"missing field [{k}]from isbn [{isbn}]")
                        row.append("")
                csvwriter.writerow(row)
        print("book info exported")

    def purge_pages_from_csv(self, input_path):
        print("purging")
        with open(input_path, "r", encoding="utf-8") as openfile:
            csv_data = [row for row in csv.DictReader(openfile)]
        for row in csv_data:
            page_title = f'BOOK: {row["title"]}'
            print(page_title)
            page = self.site.pages[page_title]
            if page.exists:
                page.delete(reason="incorrect page title")
                print(f"deleting page:{page_title}")

    def purge_idexed_books_with_bad_page_titles(self):
        print("purging")
        library = self.site.categories["Library"]
        book_list = [
            t.name for t in library if t.name != "Template for adding new books"
        ]
        for b in book_list:
            if "--BOOK" not in b:
                print(f"bad page for {b}")

                page = self.site.pages[b]
                if page.exists:
                    page.delete(reason="incorrect page title")
                    print(f"deleting page:{b}")

    def update_from_csv(
        self, input_path=None, no_skip=False, overwrite_differences=False
    ):

        with open(input_path, "r", encoding="utf-8") as openfile:
            csv_data = [row for row in csv.DictReader(openfile)]
        for row in csv_data:
            page_title = (
                (
                    f'{row["title"]} - {row["author_details"]} - ISBN:{row["isbn"]} --BOOK'
                )
                .replace("#", "")
                .replace("<", "")
                .replace(">", "")
                .replace("|", ";")
                .replace("{", "(")
                .replace("}", ")")
                .replace("_", " ")
            )

            page = self.site.pages[page_title]
            if page.exists:
                print(f"Page exists: {page_title}")
                if no_skip:
                    page_text = page.text()
                    print("updating content if needed")
                    if overwrite_differences:
                        page.edit(self.create_page_text(row), "automated update")
                    else:
                        pass

            else:
                print(f"no page for: {page_title}\n...creating page")

                page.edit(self.create_page_text(row), "automated update")

    def create_page_text(self, row):
        page_dict = {}
        text_list = []
        for key in self.bc_fields:
            page_dict[key] = row[key]
            text_list.append(f"== {key} ==")
            text_list.append(f"{row[key]}")
        text_list.append("......END OF RECORD......")

        category_set = list(
            set(
                [
                    c.strip()
                    for c in row["genre"].split("/") + ["Library"]
                    if c.strip() != ""
                ]
            )
        )
        for c in category_set:
            text_list.append(f"[[Category: {c}]]")

        text_output = "\n".join(text_list)

        print(text_output)
        print("\n\n")

        return text_output


# %% define main
def main():
    pass


# %% run main
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=str, help="mediawiki site to connect to")
    parser.add_argument("-u", "--user", type=str, help="user for connection")
    parser.add_argument("-p", "--password", type=str, help="password for connection")
    parser.add_argument(
        "-i", "--input", type=str, help="path to csv file to use for library update"
    )
    parser.add_argument(
        "-o", "--output", type=str, help="path to csv file for exporting library update"
    )
    parser.add_argument(
        "--no_skip", help="don't skip entries that already exist", action="store_true"
    )
    parser.add_argument(
        "--overwrite",
        help="overwrite values in wiki if different values in csv",
        action="store_true",
    )
    parser.add_argument(
        "--purge",
        help="removes pages --- don't do this unless you know what you are doing",
        action="store_true",
    )

    args = parser.parse_args()

    mw = mw_connection(args.user, args.password)
    if args.input:
        if args.purge:
            mw.purge_pages_from_csv(args.input)
        else:
            mw.update_from_csv(
                input_path=args.input,
                no_skip=args.no_skip,
                overwrite_differences=args.overwrite,
            )
    elif args.purge:
        mw.purge_idexed_books_with_bad_page_titles()
    if args.output:
        mw.pull_books_to_csv(output_path=args.output)

    pass
