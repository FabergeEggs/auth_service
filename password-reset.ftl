<#assign token = link?keep_after("key=")?keep_before("&")>
Reset your password: http://localhost:3000/reset-password?key=${token}

This link will expire within 12 hours.
If you didn't request this, please ignore this email.
