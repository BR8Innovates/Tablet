import com.insuremo.sdk.services.sns.model.SendEmailRequest
import com.insuremo.sdk.services.sns.model.SendSMSRequest

Map<String, Object> out = new LinkedHashMap<String, Object>()
List<String> fe = new ArrayList<String>()
for (java.lang.reflect.Field f : SendEmailRequest.class.getDeclaredFields()) {
    String ann = ""
    for (java.lang.annotation.Annotation a : f.getAnnotations()) { ann += " " + a.toString() }
    fe.add(f.getName() + ":" + f.getType().getSimpleName() + ann)
}
List<String> fs = new ArrayList<String>()
for (java.lang.reflect.Field f : SendSMSRequest.class.getDeclaredFields()) {
    String ann = ""
    for (java.lang.annotation.Annotation a : f.getAnnotations()) { ann += " " + a.toString() }
    fs.add(f.getName() + ":" + f.getType().getSimpleName() + ann)
}
out.put("emailFields", fe)
out.put("smsFields", fs)
return out
