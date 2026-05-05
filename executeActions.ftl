<#assign token = link?keep_after("key=")?keep_before("&")>
<#if rqac?has_content && rqac[0] == "UPDATE_PASSWORD">
Reset your password: http://localhost:3000/reset-password?key=${token}

This link will expire within 12 hours.
If you didn't request this, please ignore this email.
<#else>
Verify your email: http://localhost:3000/verify-email?key=${token}

This link will expire within 12 hours.
</#if>
