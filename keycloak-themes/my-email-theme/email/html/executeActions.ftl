<#assign token = link?keep_after("key=")?keep_before("&")>
<#assign frontendUrl = properties.frontendUrl!"http://158.160.90.90:3000">
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Account action required</title>
</head>
<body>
<#if requiredActions?seq_contains("UPDATE_PASSWORD")>
  <#assign actionUrl = "${frontendUrl}/reset-password/${token}">
  <p>Reset your password:</p>
  <p><a href="${actionUrl}">${actionUrl}</a></p>
  <p>This link will expire within 12 hours.</p>
  <p>If you didn't request this, please ignore this email.</p>
<#else>
  <#assign actionUrl = "${frontendUrl}/verify-email/${token}">
  <p>Verify your email:</p>
  <p><a href="${actionUrl}">${actionUrl}</a></p>
  <p>This link will expire within 12 hours.</p>
</#if>
</body>
</html>
