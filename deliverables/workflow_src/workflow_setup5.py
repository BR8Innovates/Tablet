import sys; sys.path.insert(0, ".")
from uptab import *
FR = 1188575333
rules = []
def R(api, path, label, req, typ="string", **kw):
    d = dict(Api=api, Path=path, Label=label, Required=req, DataType=typ, AppliesTo="*"); d.update(kw); rules.append(d)
R("UPDashboard", "Section", "Dashboard section", "N", "enum", EnumValues="SUMMARY,COMMISSION")
R("UPDashboard", "Scope", "Scope", "N", "enum", EnumValues="ALL,MINE")
R("UPDashboard", "ProductCode", "Product code", "N", MinLength=3, MaxLength=10, Pattern="^[A-Z0-9]+$")
R("UPShare", "Details.InsuredName", "Insured name", "N", MinLength=1, MaxLength=80)
R("UPShare", "Details.ProductName", "Product name", "N", MinLength=1, MaxLength=80)
R("UPShare", "Details.PlanName", "Plan name", "N", MinLength=1, MaxLength=80)
R("UPShare", "Details.Premium", "Premium", "N", "decimal")
R("UPShare", "Details.EffectiveDate", "Effective date", "N", "date", Pattern="^\\d{4}-\\d{2}-\\d{2}$")
save("UP_FieldRule", FR, rules, 160, "wfrule2")
