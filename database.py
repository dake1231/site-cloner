import _mysql
import MySQLdb
import sys
import MySQLdb.cursors



class MySql:

    def __init__(self):
        self.db = MySQLdb.connect(host="localhost", user="root", passwd="", db="cloner", cursorclass= MySQLdb.cursors.DictCursor)
        self.c = self.db.cursor()


    def getItem(self):
        self.c.execute("SELECT * FROM projects WHERE status=0 LIMIT 1")
        return self.c.fetchone()

    def setItemProcess(self, id):
        self.c.execute("UPDATE projects SET status=1 WHERE id=%s", (id,))
        self.db.commit()

    def setItemDone(self, path, id):
        self.c.execute("""UPDATE projects SET status=2, project_path=%s WHERE id=%s""", (path, int(id),))
        self.db.commit()