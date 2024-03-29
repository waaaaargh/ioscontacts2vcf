#!/usr/bin/python

import sys
import argparse
import sqlite3

class Property:
    def __init__(self, fstring, values):
        self.fstring, self.values = fstring, values

    @property
    def vcard_line(self):
        return self.fstring % self.values
        

class TelProperty(Property):
    """
    WARNING: This method is heavily german-centric and/or erratic.
    """
    def __init__(self, telnr):
        # check if countrycode
        self.telnr = telnr
        if self.telnr.startswith("0"):
            self.telnr = telnr.replace("0", "+49", 1)
    
        values = (self.telnr)

        Property.__init__(self, "TEL;PREF:%s", values)

class Person:
    def __init__(self, id, firstname, lastname):
        self.id = id
        self.properties = []
        if firstname is None:
            if " " in lastname:
                self.firstname, self.lastname = lastname.split(None, 1)
            else: 
                self.firstname, self.lastname = "", lastname
        elif lastname is None:
            if " " in firstname:
                self.firstname, self.lastname = firstname.split(None, 1)
            else:
                self.firstname, self.lastname = firstname, ""
        else:
            self.firstname, self.lastname = firstname, lastname
 
    @property
    def vcard(self):
        if self.lastname == "":
            name = self.firstname
        else:
            name = self.firstname+";"+self.lastname
        return """
BEGIN:VCARD
VERSION:2.1
N;CHARSET=UTF-8:%s;%s;;;
FN;CHARSET=UTF-8:%s
%s
END:VCARD
""" % (self.lastname, self.firstname, "%s %s" % (self.firstname, self.lastname), 
        "\n".join([ prop.vcard_line for prop in self.properties ]))

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Extract contacts from an iOS device sqlite \
                                                      database and export them as vCards")
    arg_parser.add_argument("infile", help="Path to Contacts database from iDevice")
    arg_parser.add_argument("outfile", help="Path where the outfile is supposed to be written")
    
    args = arg_parser.parse_args()
    if args.infile is None:
        arg_parser.help()
        sys.exit(-1)
    
    
    ## open database
    try:
        conn = sqlite3.connect(args.infile)
    except sqlite3.Error:
        print("[!] Could not open database file, are you sure it exists?")
        sys.exit(-1)
    try:
        cursor = conn.cursor()
        test_query = "SELECT (SELECT COUNT(*) FROM ABPerson), (SELECT COUNT(*) FROM ABMultiValue);"
        cursor.execute(test_query)
        result = cursor.fetchone()
        print("[i] Everything looks good, in fact we found %i entries with %i objects!" % result)
    except sqlite3.Error as e:
        print("[!] I could not find the required tables, are you sure there's something in there?") 
        print(e)
        sys.exit(-1)

    ## Extract data
    # query shamelessly stolen from http://www.devkb.org/misc/110-Manual-contact-backup-and-restore-on-iPhone
    extract_query = "select ROWID, first, last, identifier, value, record_id from ABPerson p join \
                     ABMultiValue mv on (ROWID=record_id)"
    
    persons = []

    try:
        cursor = conn.cursor()
        result = cursor.execute(extract_query)
        for row in result:
            already_in_list = [x for x in persons if x.id == row[0]]
            if len(already_in_list) == 0:
                person = Person(row[0], row[1], row[2])
            else:
                person = already_in_list[0]

            if row[4] is not None:
                person.properties.append(
                    TelProperty(row[4])
                )
                
            if len(already_in_list) == 0:
                persons.append(person)

        with open(args.outfile, "w") as outfile:
            for p in persons:
                outfile.write(p.vcard.encode('utf-8'))

    except sqlite3.Error:
        print("[!] An unspecified Error occurred")
