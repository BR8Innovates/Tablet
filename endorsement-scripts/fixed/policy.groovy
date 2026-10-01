println "Due prem:" + Policy().DuePremium.val
def skipStatus = 4
def skipFields = []
def lastLog = Policy().getLog()
def curVer = Policy()
def fieldList = context["Field_Policy"]
		.collect { it == "VAT" ? "Vat" : it }
		.findAll { !(it in skipFields) }
def rate_Policy = Endorsement().ShortRate.val
def rate = ShortRate.val
rate = (rate == null) ? rate_Policy : rate
println("lastLog: " + lastLog)
println(fieldList)

for (field in fieldList) {
	try {
		def endorField = field + "Delta"
		def policyStatus = PolicyStatus.val
		def lastValue = 0
		if (lastLog != null && policyStatus != skipStatus) {
			lastValue = nullToZero(lastLog[field].val)
		}
		def deltaValue = -lastValue * rate
		println(field + ": last=" + lastValue + " delta=" + deltaValue)
		curVer[endorField].update(deltaValue)
		curVer[field].update(lastValue + deltaValue)
	} catch (Exception e) {
		println("FAILED on " + field + ": " + e.getMessage())
	}
}
