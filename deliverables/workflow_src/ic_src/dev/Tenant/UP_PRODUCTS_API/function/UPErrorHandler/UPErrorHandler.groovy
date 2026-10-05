/**
 * UPErrorHandler - turns an exception into a structured error response and sets the HTTP status.
 * Validation problems return 400, missing role or maker-checker violations 403, state conflicts 409, platform API errors keep their status; configuration problems and anything else are 500 with a generic table-driven message (the detail goes to the log, the caller gets the trace id).
 */
import com.insuremo.icomposer.utils.IComposerAppContext
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.sdk.core.exception.ApiException

/** Message text from UP_ApiConfig; the technical fallback is used only when the configuration itself cannot be read. */
String configText(String key, String technical) {
    try {
        return ((UPDataUtil) getCommonService("UPDataUtil")).cfg(key, "*")
    } catch (Exception ignore) {
        return technical
    }
}

/** True when a platform message carries database or framework internals (index names, class names, parser positions) that must not reach the caller. */
boolean isInternalText(String message) {
    return message != null && java.util.regex.Pattern.compile("(Duplicate entry|Cannot deserialize|Exception|at \\[Source|SQL|JDBC|\\bjava\\.|\\bcom\\.|\\borg\\.|\\.groovy|Caused by)", java.util.regex.Pattern.CASE_INSENSITIVE).matcher(message).find()
}

Map<String, Object> handle(String apiName, Exception ex) {
    int status = 500
    String code = "UP-500"
    String message = configText("MsgServerError", "The request could not be processed.")
    List<Object> fieldErrors = null
    if (ex instanceof NumberFormatException) {
        // a number that passed no rule: report it as a bad request without the Java message
        status = 400
        code = "UP-400"
        message = configText("MsgInvalidNumber", "A numeric value in the request is not valid.")
    } else if (ex instanceof IllegalArgumentException) {
        status = 400
        code = "UP-400"
        message = ex.getMessage()
        if (message.startsWith("FORBIDDEN:")) {
            status = 403
            code = "UP-403"
            message = message.substring("FORBIDDEN:".length())
        } else if (message.startsWith("CONFLICT:")) {
            status = 409
            code = "UP-409"
            message = message.substring("CONFLICT:".length())
        } else if (message.startsWith("VALIDATION:")) {
            fieldErrors = (List<Object>) IComposerJsonUtils.fromJSON(message.substring("VALIDATION:".length()), List.class)
            message = "Validation failed: " + fieldErrors.size() + " field error(s)"
            code = "UP-VALIDATION"
        }
    } else if (ex.getClass().getName().endsWith("MultipleBusinessException") && String.valueOf(ex.getMessage()).startsWith("Policy Validation Error")) {
        // the platform's own policy validation (code tables, data dictionary) rejected the request: a caller problem, shown as 400 with the platform's text
        status = 400
        code = "UP-PLATFORM-VALIDATION"
        message = String.valueOf(ex.getMessage())
        if (isInternalText(message)) {
            message = configText("MsgPlatformInput", "A value in the request could not be processed.")
        }
    } else if (ex instanceof IllegalStateException) {
        // the detail (which table / key is missing) stays in the platform log; the caller gets the generic text and the trace id
        code = "UP-CONFIG"
        message = configText("MsgConfigError", "The service is not configured correctly.")
        org.slf4j.LoggerFactory.getLogger("UPErrorHandler").error("UP-CONFIG " + apiName + ": " + ex.getMessage())
    } else if (ex instanceof ApiException) {
        ApiException apiEx = (ApiException) ex
        status = apiEx.getCode() > 0 ? apiEx.getCode() : 500
        code = "UP-PLATFORM-" + status
        message = apiEx.getMessage()
        try {
            Map<String, Object> details = (Map<String, Object>) IComposerJsonUtils.fromJSON(apiEx.getResponseBody(), Map.class)
            if (details != null && details.get("message")) {
                message = String.valueOf(details.get("message"))
                if (details.get("code")) {
                    code = String.valueOf(details.get("code"))
                }
            }
        } catch (Exception ignore) {
            // keep the generic message when the platform body is not JSON
        }
        if (isInternalText(message)) {
            // the original text goes to the platform log with the trace id; the caller gets the generic text
            org.slf4j.LoggerFactory.getLogger("UPErrorHandler").error("UP-PLATFORM " + apiName + " trace " + IComposerAppContext.getTraceId() + " status " + status + ": " + message)
            message = status >= 500 ? configText("MsgServerError", "The request could not be processed.") : configText("MsgPlatformInput", "A value in the request could not be processed.")
        }
    }
    if (status >= 500 && code == "UP-500") {
        // unexpected failure: the caller only gets the generic text, the detail goes to the platform log with the trace id
        org.slf4j.LoggerFactory.getLogger("UPErrorHandler").error("UP-500 " + apiName + " trace " + IComposerAppContext.getTraceId() + ": " + ex.toString(), ex)
    }
    Map<String, Object> response = new LinkedHashMap<String, Object>()
    response.put("status", status)
    response.put("code", code)
    response.put("message", message)
    if (fieldErrors != null) {
        response.put("errors", fieldErrors)
    }
    response.put("api", apiName)
    response.put("trace_id", IComposerAppContext.getTraceId())
    ICmpHttpServletResponse().setStatus(status)
    return response
}

Map<String, Object> notFound(String apiName, String message) {
    Map<String, Object> response = new LinkedHashMap<String, Object>()
    response.put("status", 404)
    response.put("code", "UP-404")
    response.put("message", message)
    response.put("api", apiName)
    response.put("trace_id", IComposerAppContext.getTraceId())
    ICmpHttpServletResponse().setStatus(404)
    return response
}
