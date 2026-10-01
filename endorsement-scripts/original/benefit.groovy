println(ProductElementCode.val)
def lastLog = PolicyBenefit().getLog()
def curVer = PolicyBenefit()
def fieldList = context["Field_Benefit"]
def rate_Policy = Endorsement().ShortRate.val
def rate = ShortRate.val
rate = (rate == null) ? rate_Policy : rate
//verify fieldList
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
    //def newValue = 0//nullToZero(curVer[field].val)
    //println("current field is "+ newValue )
    def deltaValue = -lastValue * rate
    println("deltaValue is " + deltaValue)
    curVer[endorField].update(deltaValue)
    curVer[field].update(lastValue + deltaValue)
}
