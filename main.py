import crawler
import database
import sys

if __name__ == "__main__":

    mysql = database.MySql()
    while True:
        row = mysql.getItem()
        if row is not None:
            try:
                projectStatusUpdateQuery = mysql.setItemProcess(row['id'])
                project_url = row["project_url"]
                project_name = row["project_name"]
                user_id = str(row["user_id"])
                project_id = str(row["id"])
                print('b s')
                crawl = crawler.Crawler(
                    url=project_url,
                    project_name=project_name,
                    user_id=user_id,
                    project_id=project_id)
                print('s')

                crawl.start()
                print('a s')

            except Exception as e:
                print(e)
        else:
            print('cont')
            sys.exit()
            continue
