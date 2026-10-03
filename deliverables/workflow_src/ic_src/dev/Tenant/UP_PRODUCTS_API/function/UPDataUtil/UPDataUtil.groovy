/**
 * UPDataUtil - core helpers: configuration (UP_ApiConfig), table access, flag values, formats, error helpers.
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.services.tables.TablesSdkClient
import com.insuremo.sdk.services.tables.model.DataTableConditionVo
import com.insuremo.sdk.services.tables.model.DataTableVo
import java.math.BigDecimal
import java.time.LocalDate
import java.util.ArrayList
import java.util.Arrays
import java.util.HashMap
import java.util.List
import java.util.Map

void fail(String message) {
    // mapped to HTTP 400 by UPErrorHandler
    throw new IllegalArgumentException(message)
}

String str(Object value) {
    return value == null ? "" : String.valueOf(value).trim()
}

/** Flag values come from UP_ApiConfig (TrueValue / FalseValue), never from literals in code. */
String yes() {
    return cfg("TrueValue", "*")
}

String no() {
    return cfg("FalseValue", "*")
}

boolean isYes(Object value) {
    return str(value) == yes()
}

boolean isNo(Object value) {
    return str(value) == no()
}

/** The URL's host must be listed in UP_ApiConfig AllowedHosts and the scheme must be https before a bearer token is sent to it. */
void requireAllowedHost(String url) {
    java.net.URI uri
    try {
        uri = new java.net.URI(url)
    } catch (Exception e) {
        throw new IllegalStateException("Invalid URL in UP_ApiConfig: " + url)
    }
    List<String> hosts = Arrays.asList(cfg("AllowedHosts", "*").split(","))
    if (uri.getScheme() != "https" || uri.getHost() == null || !hosts.contains(uri.getHost())) {
        throw new IllegalStateException("URL host is not allowed by UP_ApiConfig AllowedHosts: " + str(uri.getHost()))
    }
}

/** Replaces {name} markers in a configured text. */
String fill(String text, Map<String, String> values) {
    String result = text
    for (Map.Entry<String, String> entry : values.entrySet()) {
        result = result.replace("{" + entry.getKey() + "}", entry.getValue())
    }
    return result
}

java.math.RoundingMode roundingMode() {
    return java.math.RoundingMode.valueOf(cfg("RoundingMode", "*"))
}

int moneyScale() {
    return Integer.parseInt(cfg("MoneyScale", "*"))
}

BigDecimal percentBase() {
    return new BigDecimal(cfg("PercentBase", "*"))
}

/** Configuration value from UP_ApiConfig (scope = product code or "*"). A missing key is a configuration error, never a silent default. */
Map<String, String> configMap(String scope) {
    Map<String, String> values = new HashMap<String, String>()
    for (Map<String, Object> row : getRecords("UP_ApiConfig")) {
        String rowScope = str(row.get("Scope"))
        if (rowScope == "*" || rowScope == scope) {
            String key = str(row.get("Key"))
            if (!values.containsKey(key) || rowScope == scope) {
                values.put(key, str(row.get("Value")))
            }
        }
    }
    return values
}

String cfgValue(Map<String, String> config, String key) {
    if (!config.containsKey(key)) {
        throw new IllegalStateException("Configuration missing in UP_ApiConfig: " + key)
    }
    return config.get(key)
}

String cfg(String key, String scope) {
    return cfgValue(configMap(scope), key)
}

/** Value at a path such as PolicyLobList[0].PolicyRiskList[0].DateOfBirth. */
Object pathValue(Object root, String path) {
    Object current = root
    java.util.regex.Pattern indexed = java.util.regex.Pattern.compile('^(.*)\\[(\\d+)\\]$')
    for (String part : path.split("\\.")) {
        if (!(current instanceof Map)) {
            return null
        }
        String name = part
        int index = -1
        java.util.regex.Matcher m = indexed.matcher(part)
        if (m.matches()) {
            name = m.group(1)
            index = Integer.parseInt(m.group(2))
        }
        current = ((Map<String, Object>) current).get(name)
        if (index >= 0) {
            if (!(current instanceof List) || ((List<Object>) current).size() <= index) {
                return null
            }
            current = ((List<Object>) current).get(index)
        }
    }
    return current
}

Map<String, Object> fieldError(String field, String code, String message) {
    Map<String, Object> e = new LinkedHashMap<String, Object>()
    e.put("field", field)
    e.put("code", code)
    e.put("message", message)
    return e
}

void throwValidation(List<Map<String, Object>> errors) {
    if (!errors.isEmpty()) {
        throw new IllegalArgumentException("VALIDATION:" + IComposerJsonUtils.toJSON(errors))
    }
}

LocalDate parseDate(Object value) {
    String v = str(value)
    if (v.length() < 10) {
        return null
    }
    try {
        return LocalDate.parse(v.substring(0, 10))
    } catch (Exception e) {
        return null
    }
}

/** All records of a datatable as plain maps. Read once per request (kept in the request attributes), so data changes are visible on the next request. */
List<Map<String, Object>> getRecords(String tableName) {
    org.springframework.web.context.request.RequestAttributes attributes = org.springframework.web.context.request.RequestContextHolder.getRequestAttributes()
    if (attributes == null) {
        return readRecords(tableName)
    }
    String attributeName = "UP_TABLE_CACHE"
    Map<String, List<Map<String, Object>>> tables = (Map<String, List<Map<String, Object>>>) attributes.getAttribute(attributeName, org.springframework.web.context.request.RequestAttributes.SCOPE_REQUEST)
    if (tables == null) {
        tables = new HashMap<String, List<Map<String, Object>>>()
        attributes.setAttribute(attributeName, tables, org.springframework.web.context.request.RequestAttributes.SCOPE_REQUEST)
    }
    List<Map<String, Object>> cached = tables.get(tableName)
    if (cached == null) {
        cached = readRecords(tableName)
        tables.put(tableName, cached)
    }
    return cached
}

List<Map<String, Object>> readRecords(String tableName) {
    TablesSdkClient tablesSdkClient = (TablesSdkClient) getSDK("com.insuremo.sdk.services.tables.TablesSdkClient")
    // product data of the additional products lives in its own UP_ tables (PA001 tables are never read or changed)
    Map<String, String> ownTables = ["ProductMaster": "UP_ProductMaster", "ProductPlanRelation": "UP_ProductPlanRelation", "UP_PlanBenefitRelation": "UP_PlanBenefitRelation",
                                     "ProductRule": "UP_ProductRule", "DocTemplate": "UP_DocTemplate"]
    DataTableConditionVo conditionVo = new DataTableConditionVo()
    conditionVo.setDataTableName(ownTables.get(tableName) ?: tableName)
    DataTableVo table = tablesSdkClient.dataTableApi().newGetDataTableByNameRequestBuilder()
            .dataTableConditionVo(conditionVo).doRequest().getBody()
    if (table == null || table.getRecords() == null) {
        return new ArrayList<Map<String, Object>>()
    }
    String json = IComposerJsonUtils.toJSON(table.getRecords())
    return (List<Map<String, Object>>) IComposerJsonUtils.fromJSON(json, List.class)
}

List<Map<String, Object>> filterRecords(String tableName, Map<String, Object> filters) {
    List<Map<String, Object>> result = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> record : getRecords(tableName)) {
        boolean match = true
        for (Map.Entry<String, Object> entry : filters.entrySet()) {
            if (str(record.get(entry.getKey())) != str(entry.getValue())) {
                match = false
                break
            }
        }
        if (match) {
            result.add(record)
        }
    }
    return result
}

BigDecimal toDecimal(Object value) {
    String s = str(value)
    return s ? new BigDecimal(s) : BigDecimal.ZERO
}

/** Display date, pattern from UP_ApiConfig DateFormatDoc. */
String fmtDate(Object value) {
    LocalDate date = parseDate(value)
    if (date == null) {
        return str(value)
    }
    return java.time.format.DateTimeFormatter.ofPattern(cfg("DateFormatDoc", "*")).format(date)
}

/** Display amount, pattern from UP_ApiConfig MoneyFormat. */
String fmtMoney(Object value) {
    String v = str(value)
    return v ? new java.text.DecimalFormat(cfg("MoneyFormat", "*")).format(new BigDecimal(v)) : ""
}

/** Display number, pattern from UP_ApiConfig NumberFormat. */
String fmtNumber(String v) {
    if (!v || !v.matches("-?\\d+(\\.\\d+)?")) {
        return v
    }
    return new java.text.DecimalFormat(cfg("NumberFormat", "*")).format(new BigDecimal(v))
}
