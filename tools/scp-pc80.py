# import ecg_scp as scp
import argparse
import os.path
import sys
import binascii

SCPECG_HEADER_LEN = 6
SECTION_HEADER_LEN = 16
POINTER_FIELD_LEN = 10
MIN_POINTER_FIELDS = 12
SECTION_1_TAG_TERMINATOR = 255

TAG_PATIENT_LAST_NAME = 0
TAG_PATIENT_FIRST_NAME = 1
TAG_PATIENT_ID = 2
TAG_PATIENT_SECOND_LAST_NAME = 3
TAG_PATIENT_AGE = 4
TAG_PATIENT_DATE_OF_BIRTH = 5
TAG_PATIENT_HEIGHT = 6
TAG_PATIENT_WEIGHT = 7
TAG_PATIENT_SEX = 8
TAG_PATIENT_RACE = 9
TAG_DRUGS = 10
TAG_DIAG_INDICATION = 13
TAG_ACQ_DEV_ID = 14
TAG_ANALYZ_DEV_ID = 15
TAG_ACQ_INST_DESC = 16
TAG_ANALYZ_INST_DESC = 17
TAG_ACQ_DEPT_DESC = 18
TAG_ANALYZ_DEPT_DESC = 19
TAG_REF_PHYSICIAN = 20
TAG_LATEST_PHYSICIAN = 21
TAG_TECHNICIAN_DESC = 22
TAG_ROOM_DESC = 23
TAG_DATE_ACQ = 25
TAG_TIME_ACQ = 26
TAG_FREE_TEXT = 30
TAG_ECG_SEQ_NUM = 31
TAG_HIST_DIAG_CODES = 32
TAG_DATE_TIME_ZONE = 34
TAG_TEXT_MED_HIST = 35
TAG_EOF = 255
TAG = {
    TAG_PATIENT_LAST_NAME: u'Patient Last Name',
    TAG_PATIENT_FIRST_NAME: u'Patient First Name',
    TAG_PATIENT_ID: u'Patient ID',
    TAG_PATIENT_SECOND_LAST_NAME: u'Second Last Name',
    TAG_PATIENT_AGE: u'Patient Age',
    TAG_PATIENT_DATE_OF_BIRTH: u'Patient Date of Birth',
    TAG_PATIENT_HEIGHT: u'Patient Height',
    TAG_PATIENT_WEIGHT: u'Patient Weight',
    TAG_PATIENT_SEX: u'Patient Sex',
    TAG_PATIENT_RACE: u'Patient Race',
    TAG_DRUGS: u'Drugs',
    TAG_DIAG_INDICATION: u'Diagnosis or Referral Indication',
    TAG_ACQ_DEV_ID: u'Acquiring Device Id',
    TAG_ANALYZ_DEV_ID: u'Analyzing Device Id',
    TAG_ACQ_INST_DESC: u'Acquiring Institution Description',
    TAG_ANALYZ_INST_DESC: u'Analyzing Institution Description',
    TAG_ACQ_DEPT_DESC: u'Acquiring Department Description',
    TAG_ANALYZ_DEPT_DESC: u'Analyzing Department Description',
    TAG_REF_PHYSICIAN: u'Referring Physician',
    TAG_LATEST_PHYSICIAN: u'Latest Confirming Physician',
    TAG_TECHNICIAN_DESC: u'Technician Description',
    TAG_ROOM_DESC: u'Room Description',
    TAG_DATE_ACQ: u'Date of Acquisition',
    TAG_TIME_ACQ: u'Time of Acquisition',
    TAG_FREE_TEXT: u'Free Text',
    TAG_ECG_SEQ_NUM: u'ECG Sequence Number',
    TAG_HIST_DIAG_CODES: u'History diagnostic codes',
    TAG_DATE_TIME_ZONE: u'Date Time Zone',
    TAG_TEXT_MED_HIST: u'Free-text Medical History',
    TAG_EOF: u'End of section'
}

TAGS_MANDATORY = [TAG_PATIENT_ID, TAG_ACQ_DEV_ID, TAG_DATE_ACQ, TAG_TIME_ACQ]
TAGS_TYPE_DATE = [TAG_PATIENT_DATE_OF_BIRTH, TAG_DATE_ACQ]
TAGS_TYPE_TIME = [TAG_TIME_ACQ]
TAGS_TYPE_AGE = [TAG_PATIENT_AGE]
TAGS_TYPE_ASCIIZ = [
    TAG_PATIENT_LAST_NAME,
    TAG_PATIENT_FIRST_NAME,
    TAG_PATIENT_ID,
    TAG_PATIENT_SECOND_LAST_NAME,
    TAG_DIAG_INDICATION,
    TAG_ACQ_INST_DESC,
    TAG_ANALYZ_INST_DESC,
    TAG_ACQ_DEPT_DESC,
    TAG_ANALYZ_DEPT_DESC,
    TAG_REF_PHYSICIAN,
    TAG_LATEST_PHYSICIAN,
    TAG_TECHNICIAN_DESC,
    TAG_ROOM_DESC,
    TAG_FREE_TEXT,
    TAG_ECG_SEQ_NUM,
    TAG_TEXT_MED_HIST
]
TAGS_TYPE_MACHINE_ID = [TAG_ACQ_DEV_ID, TAG_ANALYZ_DEV_ID]

ENCODING_REAL = 0
ENCODING_FIRST_DIFF = 1
ENCODING_SECOND_DIFF = 2
ENCODING = {
    ENCODING_REAL: u'Real (zero difference)',
    ENCODING_FIRST_DIFF: u'First difference',
    ENCODING_SECOND_DIFF: u'Second difference'
}

BIMODAL_COMPRESSION_FALSE = 0
BIMODAL_COMPRESSION_TRUE = 1
BIMODAL_COMPRESSION = {
    BIMODAL_COMPRESSION_FALSE: u'Not used',
    BIMODAL_COMPRESSION_TRUE: u'Bimodal'
}


def read_section_header(fp, offset):
    """ Read an SCP-ECG section header (16 bytes) and check the CRC """
    h = {}
    fp.seek(offset)
    h['crc'] = int.from_bytes(fp.read(2), byteorder='little')
    h['id'] = int.from_bytes(fp.read(2), byteorder='little')
    h['length'] = int.from_bytes(fp.read(4), byteorder='little')
    h['version'] = int.from_bytes(fp.read(1), byteorder='little')
    h['protocol'] = int.from_bytes(fp.read(1), byteorder='little')
    h['reserved'] = fp.read(6)
    fp.seek(offset + 2)
    h['calc_crc'] = binascii.crc_hqx(fp.read(h['length'] - 2), 0xffff)
    if h['crc'] != h['calc_crc']:
        print(u'ERROR: Section CRC check failed')
        sys.exit(1)
    return h

def print_section_header(i, h, label=''):
    """ Print data from the the section header """
    print()
    print(u'==== Section #%d: %s ====' % (i, label))
    print(u'Section CRC:      0x%04X' % (h['crc'],))
    print(u'Section Id:       0x%04X' % (h['id'],))
    print(u'Section length:   %d'     % (h['length'],))
    print(u'Section version:  0x%02X' % (h['version'],))
    print(u'Protocol version: 0x%02X' % (h['protocol'],))
    print(u'Calculated CRC:   0x%04X' % (h['calc_crc'],))
    
def parse_date(data):
    """ Convert a date from 4-bytes SCP-ECG format to ISO YYYY-MM-DD format """
    year = int.from_bytes(data[0:2], byteorder='little')
    month = int.from_bytes(data[2:3], byteorder='little')
    day = int.from_bytes(data[3:4], byteorder='little')
    if (month < 1 or month > 12) or (day < 1 or day > 31):
        print(u'WARNING: Invalid date: %d-%d-%d (%s)' % (year, month, day, data))
        year, month, day = 0, 0, 0
    return '%04d-%02d-%02d' % (year, month, day)

def parse_time(data):
    """ Convert a time from 3-bytes SCP-ECG format to HH:MM:SS format """
    hours = int.from_bytes(data[0:1], byteorder='little')
    minutes = int.from_bytes(data[1:2], byteorder='little')
    seconds = int.from_bytes(data[2:3], byteorder='little')
    if (hours > 23 or minutes > 59 or seconds > 59):
        print(u'WARNING: Invalid time: %d:%d:%d (%s)' % (hours, minutes, seconds, data))
        hours, minutes, seconds = 0, 0, 0
    return '%02d:%02d:%02d' % (hours, minutes, seconds)

def parse_asciiz(data):
    return data.decode('utf-8').split('\0', 1)[0]

def read_parameter(fp):
    """ Read a parameter from patient data (Section #1) """
    tag = int.from_bytes(fp.read(1), byteorder='little')
    length = int.from_bytes(fp.read(2), byteorder='little')
    value = fp.read(length)
    if tag in TAGS_TYPE_DATE:
        value = parse_date(value)
    elif tag in TAGS_TYPE_TIME:
        value = parse_time(value)
    elif tag in TAGS_TYPE_ASCIIZ:
        value = parse_asciiz(value)
 
    if tag in TAG:
        tag_label = TAG[tag]
    else:
        tag_label = u'Unknown %d' % (tag,)
    return (tag, tag_label, length, value)


MANDATORY_TAGS = [2, 14, 25, 26]


#-------------------------------------------------------------------------
# Main program.
#-------------------------------------------------------------------------
parser = argparse.ArgumentParser(description=u'Parse an SCP-ECG file and eventually dump values in CSV format.')
parser.add_argument('filename', type=str, help=u'SCP-ECG file to read')
parser.add_argument('filename_csv', nargs='?', default='', type=str, help=u'CSV file to write (default append .csv to filename)')
parser.add_argument('--millivolt', action='store_true', help=u'convert CSV values to millivolt')
parser.add_argument('--null-as-zero', action='store_true', help=u'missing values are converted to zeroes in CSV')
args = parser.parse_args()

filename = args.filename
filename_csv = None if len(args.filename_csv) < 1 else args.filename_csv
if not os.path.exists(filename):
    print(u'ERROR: Input file "%s" does not exists' % (filename,))
    sys.exit(1)

# If output CSV filename is explicit: will eventually overwrite,
# do not overwrite if instead it is implicit.
overwrite_msg = None
if filename_csv is None:
    filename_csv = filename + u'.csv'
    if os.path.exists(filename_csv):
        overwrite_msg = u'WARNING: File "%s" already exists, will not overwrite.' % (filename_csv,)
        filename_csv = None

# Get some metadata from file size.
file_size = os.path.getsize(filename)

f = open(filename, 'rb')

# ==== SCP-ECG Record, check CRC and length ====

# CRC is actually a byte by byte CRC-CCITT (0xFFFF)
record_crc = int.from_bytes(f.read(2), byteorder='little')
record_length = int.from_bytes(f.read(4), byteorder='little')
print(u'==== SCP-ECG Record ====')
print(u'File size:      %d bytes' % (file_size,))
print(u'Record CRC:     0x%04X' % (record_crc,))
print(u'Record length:  %d bytes' % (record_length,))
f.seek(2)
calculated_crc = binascii.crc_hqx(f.read(record_length - 2), 0xffff)
print(u'Calculated CRC: 0x%04X' % (calculated_crc,))
if record_crc != calculated_crc:
    print(u'ERROR: CRC check failed')
    sys.exit(1)
if file_size != record_length:
    print(u'ERROR: File length does not match record length')
    sys.exit(1)


# ==== Section #0 is the Pointer Section (mandatory) ====

# Section #0: Section ID Header
h = read_section_header(f, SCPECG_HEADER_LEN)
print_section_header(0, h, u'Section Pointers')
if h['reserved'].decode('utf-8') != u'SCPECG':
    print(u'ERROR: Missing signature "SCPECG" in Section 0')
    sys.exit(1)

# Section #0: Data Part
# Contains Pointer Fields for sections 0-11, plus manufacturer sections if any.
# NOTICE: There is a pointer section for section 0 too.
data_part_length = h['length'] - SECTION_HEADER_LEN
print(u'Data Part length: %d' % (data_part_length,))
if (data_part_length % POINTER_FIELD_LEN) != 0:
    print(u'WARNING: Data part of section #0 is %d bytes, not a multiple of %d (pointer field size)' % (data_part_length, POINTER_FIELD_LEN))
pointer_fields = int(data_part_length / POINTER_FIELD_LEN)
print(u'Pointer Fields:   %d' % (pointer_fields,))

if pointer_fields < MIN_POINTER_FIELDS:
    print(u'WARNING: Only %d pointer fields found, should be at least %d' % (pointer_fields, MIN_POINTER_FIELDS))

f.seek(SCPECG_HEADER_LEN + SECTION_HEADER_LEN)
section_pointers = {}
for i in range(0, pointer_fields):
    section_id = int.from_bytes(f.read(2), byteorder='little')
    section_len = int.from_bytes(f.read(4), byteorder='little')
    section_index = int.from_bytes(f.read(4), byteorder='little')
    section_pointers[i] = {'idx': section_index, 'length': section_len}
    print()
    print(u'==== Pointer for Section #%d ====' % (i,))
    print(u'Section Id:     0x%04X' % (section_id,))
    print(u'Section index:  0x%08X' % (section_index,))
    print(u'Section length: %d'     % (section_len,))
    if section_id != i:
        print(u'WARNING: Searching section pointer %d, found Id %d' % (i, section_id))


# ==== Section #1 contains the Patient Data (mandatory) ====

# Section indexes are 1-based.
section_index = section_pointers[1]['idx'] - 1
section_length = section_pointers[1]['length']
h = read_section_header(f, section_index)
print_section_header(1, h, u'Patient Data')
if h['id'] != 1:
    print(u'ERROR: Searching section #%d, found Id %d' % (1, h['id']))
    sys.exit(1)
f.seek(section_index + SECTION_HEADER_LEN)
read_len = 0
print()
while read_len < (section_length - SECTION_HEADER_LEN):
    tag, tag_label, length, value = read_parameter(f)
    print(u'Tag: %s: %s' % (tag_label, value))
    if tag == TAG_EOF:
        break
    read_len += (1 + 2 + length)


# ==== Section #2 contains the Huffman tables (optional) ====
section_index = section_pointers[2]['idx'] - 1
section_length = section_pointers[2]['length']
if section_length == 0:
    using_huffman = False
else:
    using_huffman = True
    h = read_section_header(f, section_index)
    print_section_header(2, h, u'Huffman tables')
    if h['id'] != 2:
        print(u'ERROR: Searching section #%d, found Id %d' % (2, h['id']))
        sys.exit(1)
    f.seek(section_index + SECTION_HEADER_LEN)
    tables_num = int.from_bytes(f.read(2), byteorder='little')
    print()
    if tables_num == 1: # DEFAULT_HUFFMAN_TABLE:
        print(u'INFO: Using SCP-ECG default Huffman table')
    else:
        print(u'ERROR: Using custom Huffman table #%d not supported' % (tables_num,))
        sys.exit(1)

using_huffman = False

# ==== Section #3 contains ECG lead definition (optional) ====
section_index = section_pointers[3]['idx'] - 1
section_length = section_pointers[3]['length']
if section_length == 0:
    print(u'ERROR: Section #3 (ECG lead definition) not found')
    sys.exit(1)
h = read_section_header(f, section_index)
print_section_header(3, h, u'ECG lead definition')
if h['id'] != 3:
    print(u'ERROR: Searching section #%d, found Id %d' % (3, h['id']))
    sys.exit(1)
f.seek(section_index + SECTION_HEADER_LEN)
leads_number = int.from_bytes(f.read(1), byteorder='little')
flag_byte = int.from_bytes(f.read(1), byteorder='little')
ref_beat     = (flag_byte & 0b00000001) == 0b001
simult_read  = (flag_byte & 0b00000100) == 0b100
lead_simult  = (flag_byte & 0b11111000) >> 3
print()
print(u'Leads: %d' % (leads_number,))
print(u'Flag byte: %s' % (bin(flag_byte),))
print(u'Reference beat: %s' % (ref_beat,))
print(u'Simultaneous read: %s' % (simult_read,))
print(u'Leads simulteaneous: %d' % (lead_simult,))
lead_sample_num = {}
max_sample_num = 0
min_sample_num = None
for i in range(0, leads_number):
    # Sample numbering is 1-based.
    starting_sample = int.from_bytes(f.read(4), byteorder='little')
    ending_sample = int.from_bytes(f.read(4), byteorder='little')
    lead_id = int.from_bytes(f.read(1), byteorder='little')
    if ending_sample > max_sample_num:
        max_sample_num = ending_sample
    if min_sample_num == None:
        min_sample_num = starting_sample
    elif starting_sample < min_sample_num:
        min_sample_num = starting_sample
    if starting_sample < 1:
        warning = u' (start shifted from %d to 1)' % (starting_sample,)
        starting_fixed = 1
    else:
        warning = u''
        starting_fixed = starting_sample
    lead_sample_num[i] = {'start': starting_fixed, 'end': ending_sample}
    print(u'Lead #%02d - Sampling interval: %d - %d%s' % (i, starting_sample, ending_sample, warning))
if min_sample_num < 1:
    print()
    print(u'WARNING: Starting sample shall start with 1')

# Now read section 5
section_index = section_pointers[5]['idx'] - 1
section_length = section_pointers[5]['length']
if section_length == 0:
    print(u'ERROR: Section #5 not found')
    sys.exit(1)
h = read_section_header(f, section_index)
print_section_header(5, h, u'Section 5')
f.seek(section_index + SECTION_HEADER_LEN)
for i in range(0, section_length):
    vv = int.from_bytes(f.read(1), byteorder='little')
    print(vv)

# ==== Section #6 contains the rhythm data (optional) ====
# Contains the entire ECG rhythm data, if no reference beats have been subtracted.
section_number = 4 # 6 in 3.0
section_index = section_pointers[section_number]['idx'] - 1
section_length = section_pointers[section_number]['length']
if section_length == 0:
    print(u'ERROR: Section #6 (rhythm data) not found')
    sys.exit(1)
h = read_section_header(f, section_index)
print_section_header(section_number, h, u'Rhythm Data')
if h['id'] != 6:
    print(u'ERROR: Searching section #%d, found Id %d' % (section_number, h['id']))
    sys.exit(1)
if ref_beat:
    print(u'ERROR: Unsupported rhythm using reference beat compression')
    sys.exit(1)
f.seek(section_index + SECTION_HEADER_LEN)
amplitude_multiplier = int.from_bytes(f.read(2), byteorder='little')  # Nanovolt
sample_time_interval = int.from_bytes(f.read(2), byteorder='little')  # Microseconds
encoding = int.from_bytes(f.read(1), byteorder='little')
bimodal_compr = int.from_bytes(f.read(1), byteorder='little')
if encoding not in ENCODING:
    print(u'ERROR: Unknown encoding mode %d, I known only "%s"' % (encoding, ENCODING))
    sys.exit(1)
if bimodal_compr not in BIMODAL_COMPRESSION:
    print(u'ERROR: Unknown compression %d' % (bimodal_compr,))
    sys.exit(1)
print()
print(u'Amplitude multiplier: %d nV' % (amplitude_multiplier,))
print(u'Sample time interval: %d us' % (sample_time_interval,))
print(u'Encoding mode: %s' % (ENCODING[encoding],))
print(u'Bimodal compression: %s' % (BIMODAL_COMPRESSION[bimodal_compr],))
print(u'Using Huffman table: %s' % (using_huffman,))
stored_bytes_lead = {}
for i in range(0, leads_number):
    stored_bytes_lead[i] = int.from_bytes(f.read(2), byteorder='little')
    print(u'Bytes used to store lead #%d data: %d' % (i, stored_bytes_lead[i]))

ecg_data = {}
ecg_raw = []
for lead in range(0, leads_number):
    data_bytes = f.read(stored_bytes_lead[lead])  # data_bytes is of type <class 'bytes'>
    print()
    print('==== Read %d bytes for lead #%d' % (len(data_bytes), lead))
    if bimodal_compr != 0:
        print(u'WARNING: Unsupported "%s" compression' % (BIMODAL_COMPRESSION[bimodal_compr],))
        continue
    if using_huffman:
        bit_decoder = huffman_decoder()
    else:
        bit_decoder = raw_decoder()
    sample_num = lead_sample_num[lead]['start']
    if encoding == ENCODING_REAL:
        for val in bit_decoder.decode(data_bytes):
            # TODO: Is there a value for NULL?
            ecg_data[(sample_num, lead)] = val
            sample_num += 1
    elif encoding == ENCODING_SECOND_DIFF:
        sequence = second_diff()
        for diff in bit_decoder.decode(data_bytes):
            # TODO: Is there a value for NULL?
            val = sequence.val(diff)
            ecg_data[(sample_num, lead)] = val
            sample_num += 1
    else:
        print(u'WARNING: Unsupported encoding mode %d: "%s"' % (encoding, ENCODING[encoding]))
        continue
    # Actual number of samples can differ from Section #3 declarations.
    print(u'INFO: Lead #%d: read %d samples' % (lead, sample_num - 1))

f.close()

ecg_raw_data = list(ecg_data.values())
plt.plot(ecg_raw_data[:600])
plt.show()

# Dump the full time serie, in CSV format.
print()
print(u'==== Saving ECG data in CSV format ====')
if overwrite_msg is not None:
    print(overwrite_msg)
if filename_csv is not None:
    f_out = open(filename_csv, 'wb')
    mult = float(amplitude_multiplier) / 1000000.0
    for sample_num in range(1, (max_sample_num + 1)):
        values_row = []
        for lead in range(0, leads_number):
            if (sample_num, lead) in ecg_data:
                values_row.append(ecg_data[(sample_num, lead)])
            else:
                values_row.append(None)
        if args.millivolt:
            row = ','.join(csv_format(x, multiplier=mult, none_as_zero=args.null_as_zero) for x in values_row)
        else:
            row = ','.join(csv_format(x, num_format=u'%d', none_as_zero=args.null_as_zero) for x in values_row)
        f_out.write(row.encode('utf-8') + b'\n')
    f_out.close()
    print(u'INFO: CSV data written to file "%s"' % (filename_csv,))


