from . import dbbase
import sqlite3
import json

DB_CONNECTION_TIMEOUT = 10

map_fieldtype = {
  "int": "int",
  "bigint": "int",
  "varchar": "text",
  "char": "text",
  "text": "text",
  "mediumtext": "text",
  "longtext": "text",
  "float": "real"
}

class SQLiteDB(dbbase.BaseDB):    
    
    def connect(self, config):                
        self._dbtype = "sqlite"
        if self._conn == None:            
            self._conn = sqlite3.connect(config["host"],
                             timeout=DB_CONNECTION_TIMEOUT,
                             isolation_level=None)
            
            self._conn.execute('PRAGMA journal_mode = WAL;')
            self._conn.execute('PRAGMA cache_size = -8000;')
            self._conn.execute('PRAGMA synchronous = NORMAL;')

            self._cursor = self._conn.cursor()
    
    def disconnect(self):
        self._cursor.close()
        self._conn.close()

    
    def beginTransaction(self):        
        self._cursor.execute("BEGIN")

    def commit(self):        
        self._cursor.execute("COMMIT")

    def rollback(self):
        self._cursor.execute("ROLLBACK")
    

    def createTable(self, tablename, definition, primarykey):
        sql = ""
        sql2 = ""
        pk = "" 
        fields = self.FieldList(tablename)
        for fielddef in definition:
            if sql != "":
                sql = sql + ","
            sql = sql + "`"+fielddef["fieldname"]+"`"+' '+map_fieldtype[fielddef["fieldtype"]]
            ## Ignore fieldsize in SQLite
            ## if fielddef["fieldsize"]>0:
            ##   sql = sql + "("+str(fielddef["fieldsize"])+")"            
            if fielddef["notnull"] == True:
                sql = sql + " NOT NULL"
            new = len(fields)>0
            for f in fields:
                if f[0].lower() == fielddef["fieldname"].lower():
                    new = False
            if new:
                if sql2 != "":
                    sql2 = sql2 + ','
                sql2 = sql2 + "ADD COLUMN `"+fielddef["fieldname"]+"`"+' '+map_fieldtype[fielddef["fieldtype"]]
                if fielddef["notnull"] == True:
                    sql2 = sql2 + " NOT NULL"

        for p in primarykey:
            if pk != "":
                pk = pk + ","
            pk = pk + "`"+p+"`"

        sql = sql = 'CREATE TABLE IF NOT EXISTS `'+tablename+'`(' + sql
        if pk != "":
            sql = sql + ", PRIMARY KEY("+pk+")"
        sql = sql + ')'        
        self._cursor.execute(sql)        

        if sql2 != "":
            self._cursor.execute('ALTER TABLE `'+tablename+'` '+sql2)


    def select(self, tablename, fieldnames, wheresql = ""):
        tablename = self.ReplaceTableName(tablename)
        sql = ""
        for fieldname in fieldnames:
            if sql!="":
                sql = sql + ","            
            sql=sql + fieldname 
        sql = "SELECT "+sql+" FROM "+tablename+' '+wheresql        
        self._cursor.execute(sql)
        data = self._cursor.fetchall()
        return data


    def insert(self, tablename, fieldnames, values):
        tablename = self.ReplaceTableName(tablename)
        ins = ""
        val = ""
        for fieldname in fieldnames:
            if ins != "":
                ins = ins + ", "
                val = val + ", "
            ins=ins + fieldname
            val=val + "?"
        sql = "INSERT INTO  `"+tablename+"`("+ins+") VALUES("+val+")"        
        self._cursor.execute(sql, values)
        return self._cursor.lastrowid


    def update(self, tablename, fieldnames, values, wheresql = ""):
        tablename = self.ReplaceTableName(tablename)
        upd = ""        
        for fieldname in fieldnames:
            if upd != "":
                upd = upd + ", "                
            upd=upd + fieldname+"=?"
            
        sql = "UPDATE "+tablename+" SET "+upd+" "+wheresql
        self._cursor.execute(sql, values)

    def delete(self, tablename,wheresql = ""):
        tablename = self.ReplaceTableName(tablename)
        self._cursor.execute("DELETE FROM `"+tablename+"` "+wheresql)        

    def execute(self, cmd):
        self._cursor.execute(cmd)
        
    def TableList(self):
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        data = self._cursor.fetchall()
        return data

    def FieldList(self, tablename):
        ## cid, name, type, notnull, dflt_value, pk  
        self._cursor.execute("PRAGMA table_info")
        data = self._cursor.fetchall()
        return data

    def IndexList(self, tablename):
        self._cursor.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name='%s'" % (tablename,))
        data = self._cursor.fetchall
        return data
    
    def escape(self, str):
        ##str = str.replace("\\","\\\\")
        return str.replace("'","''")