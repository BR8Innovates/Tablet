println "Due prem:"+Policy().DuePremium.val
println(ProductElementCode.val)
def lastLog = PolicyCoverage().getLog()
def curVer = PolicyCoverage()
def fieldList = context["Field_Cover"]
def rate_Policy = Endorsement().ShortRate.val
def rate = ShortRate.val
rate = (rate == null) ? rate_Policy : rate
//verify fieldList
println(fieldList)
for (field in fieldList) {
	println("field is " + field)
	endorField = field + "Delta"
	println("endorField is " + endorField)
	def policyStatus = PolicyStatus.val
	def lastValue = 0
	if (lastLog != null && policyStatus != 3) {
		lastValue = nullToZero(lastLog[field].val)
		println("lastValue is " + lastValue)
	}

	def deltaValue = -lastValue * rate
	println("deltaValue is " + deltaValue)

	curVer[endorField].update(deltaValue)
	curVer[field].update(lastValue + deltaValue)
}
