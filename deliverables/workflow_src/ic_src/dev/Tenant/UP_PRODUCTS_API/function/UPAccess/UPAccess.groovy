/**
 * UPAccess - who is calling and what may they do (Maker / Proposal Checker / Cancellation Checker).
 * The caller is taken from the platform token (IComposerAppContext), never from the request. Roles come from the UP_UserRole table.
 * Enforcement is switched by UP_ApiConfig RoleEnforcement (TrueValue = on); with it off the APIs behave as before.
 */
import com.insuremo.icomposer.utils.IComposerAppContext

/** The platform user behind the token: UserName, UserId, DisplayName, Email. */
Map<String, Object> currentUser() {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> user = new LinkedHashMap<String, Object>()
    user.put("UserName", util.str(IComposerAppContext.getUserName()))
    com.insuremo.icomposer.context.AppUser app = IComposerAppContext.getIComposerCurrentUser()
    user.put("UserId", app == null ? "" : util.str(app.getUserId()))
    user.put("DisplayName", app == null ? "" : util.str(app.getRealName()))
    user.put("Email", app == null ? "" : util.str(app.getEmail()))
    return user
}

/** Active role rows of a user (by user name, case-insensitive, or by platform user id). */
List<Map<String, Object>> roleRows(String userName, String userId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> row : util.getRecords("UP_UserRole")) {
        if (!util.isYes(row.get("IsActive"))) {
            continue
        }
        boolean byName = userName && util.str(row.get("UserName")).equalsIgnoreCase(userName)
        boolean byId = userId && util.str(row.get("UserId")) == userId
        if (byName || byId) {
            rows.add(row)
        }
    }
    return rows
}

/** Caller identity with roles, branch and contact details. Roles is empty when the user is not in UP_UserRole. */
Map<String, Object> me() {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> user = currentUser()
    List<Map<String, Object>> rows = roleRows(util.str(user.get("UserName")), util.str(user.get("UserId")))
    List<String> roles = new ArrayList<String>()
    for (Map<String, Object> row : rows) {
        roles.add(util.str(row.get("Role")))
    }
    Map<String, Object> out = new LinkedHashMap<String, Object>()
    out.put("UserName", user.get("UserName"))
    out.put("UserId", user.get("UserId"))
    out.put("DisplayName", rows.isEmpty() ? user.get("DisplayName") : (util.str(rows.get(0).get("DisplayName")) ?: user.get("DisplayName")))
    out.put("Email", rows.isEmpty() ? user.get("Email") : (util.str(rows.get(0).get("Email")) ?: user.get("Email")))
    out.put("Branch", rows.isEmpty() ? "" : util.str(rows.get(0).get("Branch")))
    out.put("Roles", roles)
    out.put("RoleEnforcement", util.cfg("RoleEnforcement", "*"))
    out.put("AllowSelfApproval", util.cfg("AllowSelfApproval", "*"))
    return out
}

/** Stops the call (HTTP 403, UP-403) unless the caller holds one of the roles. Returns the caller identity. With RoleEnforcement off nothing is checked. */
Map<String, Object> require(List<String> allowedRoles) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    Map<String, Object> caller = me()
    if (!util.isYes(util.cfg("RoleEnforcement", "*"))) {
        return caller
    }
    List<String> held = (List<String>) caller.get("Roles")
    for (String role : allowedRoles) {
        if (held.contains(role)) {
            return caller
        }
    }
    throw new IllegalArgumentException("FORBIDDEN:" + util.cfg("MsgForbidden", "*"))
}

/** Maker-checker rule: the person who created an item cannot approve or reject it (unless AllowSelfApproval is on). */
void requireNotCreator(Map<String, Object> caller, String creatorUserId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (!util.isYes(util.cfg("RoleEnforcement", "*")) || util.isYes(util.cfg("AllowSelfApproval", "*"))) {
        return
    }
    if (creatorUserId && util.str(caller.get("UserId")) == creatorUserId) {
        throw new IllegalArgumentException("FORBIDDEN:" + util.cfg("MsgSelfApproval", "*"))
    }
}

/** Any role holder (read access to policy data). */
Map<String, Object> requireAny() {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    return require(Arrays.asList(util.cfg("RoleMaker", "*"), util.cfg("RoleProposalChecker", "*"), util.cfg("RoleCancellationChecker", "*")))
}

/** A maker may only change what they created. */
void requireCreator(Map<String, Object> caller, String creatorUserId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    if (!util.isYes(util.cfg("RoleEnforcement", "*"))) {
        return
    }
    if (creatorUserId && util.str(caller.get("UserId")) != creatorUserId) {
        throw new IllegalArgumentException("FORBIDDEN:" + util.cfg("MsgNotOwner", "*"))
    }
}

/** Role holders (for staff alerts): rows with the role that have an email or mobile number. */
List<Map<String, Object>> holdersOf(String role) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    List<Map<String, Object>> out = new ArrayList<Map<String, Object>>()
    for (Map<String, Object> row : util.getRecords("UP_UserRole")) {
        if (util.isYes(row.get("IsActive")) && util.str(row.get("Role")) == role) {
            out.add(row)
        }
    }
    return out
}

/** One user's contact details by platform user id (the maker of a proposal); empty map when unknown. */
Map<String, Object> contactOf(String userId) {
    UPDataUtil util = (UPDataUtil) getCommonService("UPDataUtil")
    for (Map<String, Object> row : util.getRecords("UP_UserRole")) {
        if (util.isYes(row.get("IsActive")) && util.str(row.get("UserId")) == userId) {
            return row
        }
    }
    return new HashMap<String, Object>()
}
