"""@package docstring
This script finds all the EPICS db files in a given directory and parses the record
and field data into python classes. Arrays of Record instances can then be analysed
to find records that lack specific fields etc.
"""
import unittest
from loader import FileHolder
import xmlrunner
import argparse
import re
import sys

# list of those record types that should have a EGU field
EGU_list = {'ai', 'ao', 'calc', 'calcout', 'compress', 'dfanout', 'longin', 'longout', 'mbbo', 'mbboDirect',
            'permissive', 'sel', 'seq', 'state', 'stringin', 'stringout', 'subArray', 'sub', 'waveform', 'archive',
            'cpid', 'pid', 'steppermotor'}

EGU_sub_list = {'longin', 'longout', 'ai', 'ao'}

# list of the accepted units (standard prefixs to these units are also accepted and checked for below)
allowed_units = {'A', 'angstrom', 'bar', 'bit', 'byte', 'C', 'count', 'degree', 'eV', 'hour', 'Hz', 'inch',
                 'interrupt', 'K', 'L', 'm', 'min', 'minute', 'ohm', '%', 'photon', 'pixel', 'radian', 's', 'torr',
                 'step', 'V', 'mT', 'uT', 'Oersted'}

recs = []


class TestPVUnits(unittest.TestCase):

    def test_interest_units(self):
        """
        This method checks that interesting fields have units
        """
        err = 0

        for rec in recs:
            rec_type = rec.get_type()

            if rec.is_interest() and not rec.is_disable() and (rec_type in EGU_sub_list):
                unit = rec.get_field("EGU")

                if len(unit) == 0:
                    err += 1
                    print "ERROR: Missing units on " + str(rec)
                elif unit[0] == "":
                    print "WARNING: Blank units on " + str(rec)

        self.assertEqual(err, 0, msg="Missing units on interesting PVs in project")

    def test_desc_length(self):
        """
        This method checks that the description length on dbs is no longer than 40 chars
        """

        err = 0
        for rec in recs:
            descs = rec.get_field("DESC")

            for desc in descs:
                # remove macros
                desc = re.sub(r'\$\([^)]*\)', '', desc)

                if len(desc) > 40:
                    err += 1
                    print "ERROR: Description too long on " + str(rec)

        self.assertEqual(err, 0, msg="Overly long description in project")

    def allowed_unit(self, unit):
        """
        This method checks that the given unit conforms to standard
        """
        if unit in allowed_units:
            return True

        # otherwise check for macro
        if unit[0] == "$":
            return True

        # otherwise split unit amalgamations
        units = re.split(r'[/ ()]', unit)
        for u in units:
            if not (u in allowed_units):
                # may be to the power of
                if not (re.match(r"\^[-]?\d", u)):
                    # may be prefixed
                    if not (re.match(r'T|G|M|k|m|u|n|p|f', u[0]) and u[1:] in allowed_units):
                        # special case of cm
                        if not u == "cm":
                            return False

        return True

    def test_units_valid(self):
        """
        This method loops through all found records and finds the unique units. It then checks these units are standard
        """

        # Holds the records sorted by unit
        saved_units = dict({})
        unit_label = []
        units_array = []
        invalid = 0

        for rec in recs:
            unit = rec.get_field("EGU")

            # add the units to the appropriate place in the dictionary
            if len(unit) == 1 and unit[0] != "":
                if unit[0] in saved_units:
                    saved_units[unit[0]] += 1
                    unit_label[unit_label.index(unit[0])].append(rec)
                else:
                    saved_units[unit[0]] = 1
                    unit_label.append(unit[0])
                    units_array.append([])
                    units_array[unit_label.index(unit[0])].append(rec)
                if not self.allowed_unit(unit[0]):
                    invalid += 1
                    try:
                        unicode(str(unit[0]), 'ascii')
                    except UnicodeDecodeError:
                        str_unit = ""
                    else:
                        str_unit = " (" + str(unit[0]) + ")"

                    print "ERROR: Invalid units" + str_unit + " on " + str(rec)

            if len(unit) > 1:
                print "WARNING: Multiple units on " + str(rec)

        print "Units in project and number of instances: " + str(saved_units)

        self.assertEqual(invalid, 0, "Invalid units in project")

    def test_interest_descriptions(self):
        """
        This method checks all records marked as interesting for description fields
        """
        err = 0
        for rec in recs:
            if rec.is_interest() and len(rec.get_field("DESC")) != 1:
                print "ERROR: Missing description on " + str(rec)
                err += 1

        self.assertEqual(err, 0, msg="Missing or duplicate description on interesting PVs in project")

    def test_interest_syntax(self):
        """
        This method tests that all interesting PVs are capitalised and contain only A-Z 0-9 _ :
        """
        for rec in recs:
            if rec.is_interest():
                mypv = re.sub(r'\$\(.*\)', '', rec.pv)  # remove macros
                se = re.search(r'[^\w:]', mypv)
                self.assertTrue(se is None, "ERROR: " + rec.pv + " contains illegal characters")
                if len(mypv) > 0 and not mypv.isupper():
                    print "WARNING: " + rec.pv + " should be upper-case"


def set_up(directories):
    """
    This set up method loads and parses the db and template files prior to testing.
    """

    global recs

    dbs = FileHolder()

    for directory in directories:
        for file_type in ['.db', '.template']:
            dbs.load_files(directory, file_type)

    num = dbs.get_file_num()
    print "Number of EPICS dbs Found: " + str(num)

    # dbs.saveChecked()

    recs = dbs.parse_files()

    print "Num of recs: " + str(len(recs))


DEFAULT_DIRECTORY = '..\\..\\..\\test-reports'

if __name__ == '__main__':
    """
    Runs the unit tests
    """

    default_dirs = ['..\\..\\..\\ioc', '..\\..\\..\\support', '..\\..\\..']

    # Get output directory from command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output_dir', nargs=1, type=str, default=[DEFAULT_DIRECTORY],
                        help='The directory to save the test reports')
    parser.add_argument('-i', '--input_dir', nargs='+', type=str, default=[default_dirs],
                        help='The input directories to look for db files within')
    args = parser.parse_args()
    xml_dir = args.output_dir[0]

    # Load files
    set_up(args.input_dir)

    # Load tests
    units_suite = unittest.TestLoader().loadTestsFromTestCase(TestPVUnits)

    print "\n\n------ BEGINNING PV UNIT TESTS ------"

    ret_vals = list()
    ret_vals.append(xmlrunner.XMLTestRunner(output=xml_dir).run(units_suite).wasSuccessful())

    print "------ PV UNIT TESTS COMPLETE ------\n\n"

    # Return failure exit code if a test failed
    sys.exit(False in ret_vals)