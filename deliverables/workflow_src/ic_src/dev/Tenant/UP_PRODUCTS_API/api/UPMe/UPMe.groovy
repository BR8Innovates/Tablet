/**
 * Who am I: the caller taken from the platform token with the roles configured in UP_UserRole.
 * Response: UserName, UserId, DisplayName, Email, Branch, Roles[] (MAKER, PROPOSAL_CHECKER, CANCELLATION_CHECKER), RoleEnforcement, Insurer.
 */
UPErrorHandler errorHandler = (UPErrorHandler) getCommonService("UPErrorHandler")
try {
    UPAccess access = (UPAccess) getCommonService("UPAccess")
    return access.me()

} catch (Exception ex) {
    return errorHandler.handle("UPMe", ex)
}
