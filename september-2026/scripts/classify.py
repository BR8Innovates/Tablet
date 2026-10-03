"""Normalise raw error strings and map them to the 12 root-cause categories used in the August workbook."""
import json, re

AUG_MAP = json.load(open('aug_category_map.json'))

# Labels the August workbook used for generic Digit error envelopes that carry no validation message.
def normalise(e):
    e = (e or '').strip()
    e = re.sub(r'(Invalid RTO identified from registration number)\s*=\s*\S+', r'\1 (see RegistrationNo column)', e)
    e = re.sub(r'\b1197-\d+ - Referral triggered from the moratorium', '1197-<id> - Referral triggered from the moratorium', e)
    e = re.sub(r'(Long term TP policy exists,)\s*\S+', r'\1 <policy no>', e)
    e = re.sub(r'JSON parse error: Could not parse \S+; nested exception.*?\["(\w+)"\]\)?',
               r'JSON parse error: invalid date format in "\1"', e, flags=re.S)
    if e.startswith('JSON parse error: Could not parse'):
        e = 'JSON parse error: invalid date format in "manufactureDate"'
    m = re.match(r'Error occured during iHub integration transformation for url \S*?/fibein/1\.0/(\S+?)\.\s*Details\s*:\s*(.*)', e, re.S)
    if m:
        det = m.group(2)
        if '@route.' in det:
            det = 'unresolved route placeholder (@route.il.host@…) – IL endpoint not configured'
        elif 'outtrf' in det:
            det = 'response-transformation rule failed (%s)' % (det.split(' error')[0].replace('eval rule ', ''))
        e = 'iHub transformation error [%s]: %s' % (m.group(1), det)
    m = re.match(r'Error occured while calling iHub integration service at url \S*?/fibein/1\.0/(\S+)', e)
    if m:
        e = 'iHub service call error [%s]' % m.group(1).rstrip('.')
    e = re.sub(r'^429 \{"message":"Limit Exceeded"\}$', '429 Limit Exceeded (rate limit)', e)
    e = re.sub(r',?"traceId":"[0-9a-f-]+"', '', e)                     # strip per-call trace ids
    e = re.sub(r'^\[\d{4}-\d{2}-\d{2} [\d:.]+\]\s*', '', e)               # strip log-timestamp prefix
    e = e.replace('\r\n', '\n')
    e = re.sub(r'[*?~]', ' ', e)   # these are SUMIFS wildcards in Excel
    return e[:240]


RULES = [
    ('System/Technical Error', r'(?i)iHub|Unable to execute request|Unexpected Exception|Orbit|SQL error|ClsBLZ|out of bounds|endpoint takes|Forbidden|Limit Exceeded|timed out|timeout|ETIMEDOUT|Gateway|status code|PARTIAL_CONTENT|unable to service|intermediateEligibility|NoSuchMethod|Endpoint|Empty response|status=None|errorCode: .* \(no validationMessages\)|Internal Server Error|Unauthorized$|Response body is null|Orbit exception|IMD|HTTP \d{3}|Bad Gateway|ESOCKET'),
    ('Underwriting Rule / Referral', r'Referral|UW\d*\b|UW rules|CIBIL|ERR\d+|moratorium|UWPK|Policy issuance|DECLINE|declined|underwrit'),
    ('Third-Party Cover Rule', r'\bTP\b|Third Party|Third-Party|TP policy'),
    ('RTO / Registration Data', r'RTO|registration number|Registration'),
    ('Date/Policy Validity Rule', r'inception|Policy Start Date|date of the policy|expiry|Expiry|Previous policy|start date'),
    ('Vehicle Data Mismatch (Vahan)', r'Vahan|Cubic Capacity|Fuel Type|Vehicle Type'),
    ('Bundle/Add-on Configuration', r'bundle|Varient|Variant|Pearl|add-on|addon'),
    ('Mandatory Field Missing', r'mandatory|should not be empty|should not be blank|can not be blank|cannot be blank|is required|must be provided'),
    ('Invalid Input Value', r'Invalid|invalid|JSON parse|Length of|policy type|not match|Only Two-Wheeler|Please select'),
    ('Pricing/Limit Breach', r'exceeded the limit|ex-showroom|limit allowable'),
    ('Renewal/Policy State Issue', r'renew'),
]


def categorise(norm_err):
    if norm_err in AUG_MAP:
        return AUG_MAP[norm_err]
    for cat, pat in RULES:
        if re.search(pat, norm_err):
            return cat
    return 'Other/Uncategorized'


# who owns the fix (indicative; applied identically to every month so comparisons are like-for-like)
OWNER_BY_CATEGORY = {
    'Underwriting Rule / Referral': 'Carrier', 'Third-Party Cover Rule': 'Carrier',
    'Pricing/Limit Breach': 'Carrier', 'Renewal/Policy State Issue': 'Carrier',
    'RTO / Registration Data': 'Fibe Mapping',
    'Bundle/Add-on Configuration': 'Fibe', 'Mandatory Field Missing': 'Fibe', 'Date/Policy Validity Rule': 'Fibe',
    'Vehicle Data Mismatch (Vahan)': 'Fibe', 'Invalid Input Value': 'Fibe',
    'System/Technical Error': 'Unclassified', 'Other/Uncategorized': 'Unclassified',
}


def owner(category):
    return OWNER_BY_CATEGORY.get(category, 'Unclassified')
