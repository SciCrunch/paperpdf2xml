import sqlite3
import functools
from array import array


class GloveHandler:
    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA synchronous = OFF")
        cursor.execute("PRAGMA journal_mode = MEMORY")
        self.conn.commit()
        cursor.close()


    def close(self):
        if self.conn:
            self.conn.close()

    @functools.lru_cache(maxsize=65536)
    def get_glove_vec(self, term):
        sql = "select vector from glove_vecs where term = :term"
        cursor = self.conn.cursor()
        cursor.execute(sql, {"term": term})
        vec_blob = cursor.fetchone()
        cursor.close()
        if vec_blob:
            arr = array('f')
            arr.fromstring(vec_blob[0])
            glove_vec = arr.tolist()
        else:
            return None
        return glove_vec

