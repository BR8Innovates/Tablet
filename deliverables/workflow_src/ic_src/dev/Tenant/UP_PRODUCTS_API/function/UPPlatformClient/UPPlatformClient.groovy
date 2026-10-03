/**
 * UPPlatformClient - calls platform services (endorsement) with the caller's own token.
 * Returns { status: <http status>, body: <response text> } and never throws for HTTP or platform errors.
 */
import com.insuremo.icomposer.utils.IComposerAppContext
import com.insuremo.icomposer.utils.IComposerJsonUtils
import com.insuremo.icomposer.utils.IComposerRestTemplateManager
import org.springframework.http.HttpEntity
import org.springframework.http.HttpHeaders
import org.springframework.http.HttpMethod
import org.springframework.http.ResponseEntity
import org.springframework.web.client.RestClientResponseException
import org.springframework.web.client.RestTemplate

Map<String, Object> call(String method, String path, Object body) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    String base = util.cfg("GatewayUrl", "*")
    util.requireAllowedHost(base)
    HttpHeaders headers = new HttpHeaders()
    headers.set("Content-Type", "application/json")
    headers.set("x-mo-tenant-id", IComposerAppContext.getTenantCode())
    headers.set("Authorization", "Bearer " + IComposerAppContext.getAccessToken())
    HttpEntity<Object> entity = body == null ? new HttpEntity<Object>(headers) : new HttpEntity<Object>(body, headers)
    RestTemplate restTemplate = (RestTemplate) IComposerRestTemplateManager.remoteCall()
    Map<String, Object> result = new HashMap<String, Object>()
    try {
        ResponseEntity<Object> response = restTemplate.exchange(base + path, HttpMethod.valueOf(method), entity, Object.class)
        result.put("status", response.getStatusCodeValue())
        Object responseBody = response.getBody()
        result.put("body", responseBody == null ? "" : (responseBody instanceof String ? responseBody : IComposerJsonUtils.toJSON(responseBody)))
    } catch (RestClientResponseException ex) {
        result.put("status", ex.getRawStatusCode())
        result.put("body", ex.getResponseBodyAsString())
    } catch (Exception ex) {
        // the platform's REST template raises its own business exception for error responses
        result.put("status", 500)
        result.put("body", String.valueOf(ex.getMessage()))
    }
    return result
}

Map<String, Object> parse(Map<String, Object> response) {
    String text = String.valueOf(response.get("body") ?: "")
    if (!text.trim().startsWith("{")) {
        return new HashMap<String, Object>()
    }
    return (Map<String, Object>) IComposerJsonUtils.fromJSON(text, Map.class)
}
