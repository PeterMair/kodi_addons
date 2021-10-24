#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
from sqlite3.dbapi2 import DateFromTicks
from mairpeter.database import load, advancedsettings
from functools import wraps


from . import variables as v, app

DB_WRITE_ATTEMPTS = 100
DB_WRITE_ATTEMPTS_TIMEOUT = 1  # in seconds
DB_CONNECTION_TIMEOUT = 10


class LockedDatabase(Exception):
    """
    Dedicated class to make sure we're not silently catching locked DBs.
    """
    pass


def catch_operationalerrors(method):
    """
    sqlite.OperationalError is raised immediately if another DB connection
    is open, reading something that we're trying to change

    So let's catch it and try again

    Also see https://github.com/mattn/go-sqlite3/issues/274
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        attempts = DB_WRITE_ATTEMPTS
        while True:
            try:
                return method(self, *args, **kwargs)
            except Exception as err:
                if 'database is locked' not in err:
                    # Not an error we want to catch, so reraise it
                    raise
                attempts -= 1
                if attempts == 0:
                    # Reraise in order to NOT catch nested OperationalErrors
                    raise LockedDatabase('Database is locked')
                # Need to close the transactions and begin new ones
                self.kodiconn.commit()
                if self.artconn:
                    self.artconn.commit()
                if app.APP.monitor.waitForAbort(DB_WRITE_ATTEMPTS_TIMEOUT):
                    # PKC needs to quit
                    return
                # Start new transactions
                self.kodiconn.beginTransaction()
                if self.artconn:
                    self.artconn.beginTransaction()
    return wrapper


def _initial_db_connection_setup(conn):
    """
    Set-up DB e.g. for WAL journal mode, if that hasn't already been done
    before. Also start a transaction
    """
    conn.beginTransaction()  


def connect(media_type=None):
    """
    Open a connection to the Kodi database.
        media_type: 'video' (standard if not passed), 'plex', 'music', 'texture'

    Table-Replacement in Plex database:
      show -> tvshow (SHOW is reserved word in MySQL)
    """
    db_path = ""
    if media_type == "plex":
        conn = load.loadDB("plex")  
        conn.AddTableReplace("show","tvshow")      
    elif media_type == 'plex-copy':        
        config = advancedsettings.DBConfigFromAdvancedSettings("plex")        
        if config["type"]=="mysql":
            config["database"] = "plex_copy"
            conn = load.loadDBFromConfig(config)   
        else:
            conn = load.loadDB("plex_copy")          
        conn.AddTableReplace("show","tvshow")       
    elif media_type == "music":
        conn = load.loadDB("music", "MyMusic%s" % (v.DB_MUSIC_VERSION,))           
    elif media_type == "texture":
        db_path = "Textures" + str(v.DB_TEXTURE_VERSION)
        conn =load.loadDB(db_path)
    else:
        conn = load.loadDB("video","MyVideos%s" % (v.DB_VIDEO_VERSION,))                
    attempts = DB_WRITE_ATTEMPTS
    while True:
        try:
            _initial_db_connection_setup(conn)
        except Exception as err:
            if 'database is locked' not in err:
                # Not an error we want to catch, so reraise it
                raise
            attempts -= 1
            if attempts == 0:
                # Reraise in order to NOT catch nested OperationalErrors
                raise LockedDatabase('Database is locked')
            if app.APP.monitor.waitForAbort(0.05):
                # PKC needs to quit
                raise LockedDatabase('Database was locked and we need to exit')
        else:
            break
    return conn
