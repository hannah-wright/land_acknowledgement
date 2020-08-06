import os
import re
import psycopg2
from psycopg2.extras import DictCursor
from .logger import logger


class GeoData():
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL', default='postgresql://postgres:postgres@postgres')
        self.connection = None

    def connect(self):
        try:
            self.connection = psycopg2.connect(self.db_url)
        except psycopg2.DatabaseError as e:
            logger.error(e)
            raise e
        finally:
            logger.info('Connected to database')

    def query_location(self, location):
        '''
        Find a place and coordinates using fuzzy name matching.
        '''
        if re.match(r'^\d{5}(-\d{4})?$', location):
            return self.query_zip(location)

        smushed_name = re.sub(r'\W+', '', location).upper()

        query = '''
            SELECT city, state, state_code, latitude, longitude from geo
            WHERE UPPER(concat(city, state)) = %(s)s
            OR UPPER(concat(city, state_code)) = %(s)s
            OR metaphone(concat(city, state), 10) = metaphone(%(s)s, 10)
            OR metaphone(concat(city, state_code), 10) = metaphone(%(s)s, 10)
            LIMIT 1
            '''
        with self.connection.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, {'s': smushed_name})
            return cur.fetchone()

    def query_zip(self, zipcode):
        '''
        Find a place and coordinates from zip code. The DB only has 5-digit codes
        This will strip off the plus-4 if it's there.
        '''
        zipcode, *ext = zipcode.split('-')
        if not re.match(r'^\d{5}$', zipcode):
            raise ValueError("Cannot parse this zip code.")

        query = '''
            SELECT city, state, state_code, latitude, longitude from geo
            WHERE zipcode = %s
            LIMIT 1
            '''
        with self.connection.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, (zipcode, ))
            return cur.fetchone()

    def native_land_from_point(self, lat, lon):
        '''
        Lookup native land that contains point.
        Point is interpetered as srid 4326 (WGS 84 : https://spatialreference.org/ref/epsg/4326/)
        '''
        query = '''
        SELECT id, name
        FROM indigenousterritories
        WHERE ST_Contains(wkb_geometry,ST_GeometryFromText('POINT( %s %s)', 4326) );
        '''
        with self.connection.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(query, (lon, lat))
            return cur.fetchone()
