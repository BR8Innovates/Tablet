/**
 * UPSecurity - request hygiene shared by every API.
 *  readInput          the body must be a JSON object (anything else is a 400, never a 500); it is scanned before any API logic runs
 *  scan               blocked characters in every text value, extra allow-list for free-text fields (400 INVALID_CHARACTER)
 *  stripServerOwned   fields the server owns (policy number, ids, status) are never taken from the caller
 *  defaultOrgCode     a proposal always carries a branch that the platform code table PubBranch accepts
 * The baselines below are security controls: when UP_ApiConfig has the key (BlockedCharacters, FreeTextFields, FreeTextPattern,
 * ServerOwnedFields, OrgCode) the table value is used, otherwise the built-in baseline applies (never an error).
 */
import com.insuremo.icomposer.utils.IComposerJsonUtils
import java.util.ArrayList
import java.util.Arrays
import java.util.HashSet
import java.util.List
import java.util.Map
import java.util.Set
import java.util.regex.Pattern

/** Control characters and the characters used for script, template, shell and expression injection. */
String blockedBaseline() {
    return '[\\x00-\\x1F\\x7F<>${}`\\\\|^~;]'
}

/** Free-text fields: letters of any script, digits, space and . , ' - / @ + ( ) only. */
String freeTextBaseline() {
    return '^[\\p{L}\\p{M}0-9 .,\\x27\\-/@+()]*$'
}

String freeTextFieldsBaseline() {
    return "InsuredName,Address,BeneficaryName,CancelReason,OtherCancelReason,ProposalRejectDesc"
}

String serverOwnedBaseline() {
    return "PolicyNo,PolicyId,PolicyElementId,ProposalStatus,PolicyStatus,AgentCode"
}

String orgCodeBaseline() {
    return "1"
}

int maxFindings() {
    return 20
}

/** Optional table override of a baseline. */
String setting(String key, String baseline) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, String> config = util.configMap("*")
    return config.containsKey(key) && config.get(key) ? config.get(key) : baseline
}

/** The request body as a map, already checked by scan(). Null is an empty request; an array, text or number is a 400. */
Map<String, Object> readInput(Object body) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (body == null) {
        return new HashMap<String, Object>()
    }
    if (!(body instanceof Map)) {
        List<Map<String, Object>> errors = new ArrayList<Map<String, Object>>()
        errors.add(util.fieldError("body", "INVALID_BODY", "The request body must be a JSON object"))
        util.throwValidation(errors)
    }
    Map<String, Object> copy = (Map<String, Object>) IComposerJsonUtils.fromJSON(IComposerJsonUtils.toJSON(body), Map.class)
    Map<String, Object> input = copy == null ? new HashMap<String, Object>() : copy
    scan(input)
    return input
}

/** Rejects blocked characters in any text value, and anything outside the allow-list in the free-text fields. The value is never echoed. */
void scan(Map<String, Object> input) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Pattern blocked = Pattern.compile(setting("BlockedCharacters", blockedBaseline()))
    Pattern freeText = Pattern.compile(setting("FreeTextPattern", freeTextBaseline()))
    Set<String> freeFields = new HashSet<String>(Arrays.asList(setting("FreeTextFields", freeTextFieldsBaseline()).split(",")))
    List<Map<String, Object>> errors = new ArrayList<Map<String, Object>>()
    scanValue(input, "", "", blocked, freeText, freeFields, errors, util)
    util.throwValidation(errors)
}

void scanValue(Object value, String path, String key, Pattern blocked, Pattern freeText, Set<String> freeFields, List<Map<String, Object>> errors, UPDataUtil util) {
    if (errors.size() >= maxFindings()) {
        return
    }
    if (value instanceof Map) {
        for (Map.Entry<String, Object> entry : ((Map<String, Object>) value).entrySet()) {
            scanValue(entry.getValue(), path.isEmpty() ? entry.getKey() : path + "." + entry.getKey(), entry.getKey(), blocked, freeText, freeFields, errors, util)
        }
    } else if (value instanceof List) {
        List<Object> items = (List<Object>) value
        for (int i = 0; i < items.size(); i++) {
            scanValue(items.get(i), path + "[" + i + "]", key, blocked, freeText, freeFields, errors, util)
        }
    } else if (value instanceof String) {
        String text = (String) value
        if (blocked.matcher(text).find()) {
            errors.add(util.fieldError(path, "INVALID_CHARACTER", "The value contains a character that is not allowed"))
        } else if (freeFields.contains(key) && !freeText.matcher(text).matches()) {
            errors.add(util.fieldError(path, "INVALID_CHARACTER", "Only letters, digits, space and . , ' - / @ + ( ) are allowed"))
        }
    }
}

/** Removes the top-level fields the server owns. The platform sets the proposal status itself; a status sent by the caller made the platform fail (HTTP 500 / 502), so it is dropped. */
void stripServerOwned(Map<String, Object> input) {
    for (String name : setting("ServerOwnedFields", serverOwnedBaseline()).split(",")) {
        input.remove(name.trim())
    }
}

/** A branch the platform accepts (code table PubBranch); the caller's own OrgCode is kept. */
void defaultOrgCode(Map<String, Object> input) {
    if (!input.get("OrgCode")) {
        input.put("OrgCode", setting("OrgCode", orgCodeBaseline()))
    }
}
