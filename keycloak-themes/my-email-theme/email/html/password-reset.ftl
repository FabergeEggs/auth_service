<#assign token = link?keep_after("key=")?keep_before("&")>
<#assign frontendUrl = properties.frontendUrl!"http://158.160.90.90:3000">
<#assign resetUrl = "${frontendUrl}/reset-password/${token}">
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Reset your password</title>
</head>
<body>
  <p>Reset your password:</p>
  <p><a href="${resetUrl}">${resetUrl}</a></p>
  <p>This link will expire within 12 hours.</p>
  <p>If you didn't request this, please ignore this email.</p>
</body>
</html>
