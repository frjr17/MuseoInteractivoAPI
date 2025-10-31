# scripts/integration_test.ps1
# Integration test script for Users endpoints (PowerShell)
# Usage: run this from project root while Flask app is running:
#   .\.venv\Scripts\Activate.ps1
#   Start the Flask app in another terminal (flask run)
#   .\scripts\integration_test.ps1

$base = 'http://127.0.0.1:5000'

function Send-Request {
    param(
        [string]$Method,
        [string]$Uri,
        $Body = $null,
        $WebSession = $null
    )

    if ($Body -ne $null) {
        $json = $Body | ConvertTo-Json -Depth 10
    } else {
        $json = $null
    }

    try {
        if ($Method -in @('GET','DELETE')) {
            $resp = Invoke-WebRequest -Uri $Uri -Method $Method -WebSession $WebSession -ErrorAction Stop
        } else {
            $resp = Invoke-WebRequest -Uri $Uri -Method $Method -Body $json -ContentType 'application/json' -WebSession $WebSession -ErrorAction Stop
        }
        $content = $resp.Content
        $parsed = $null
        if ($content) { try { $parsed = $content | ConvertFrom-Json } catch { $parsed = $content } }
        return @{ Success = $true; Status = [int]$resp.StatusCode; Content = $content; Parsed = $parsed }
    } catch {
        $err = $_.Exception
        $status = $null
        $respContent = $null
        if ($err.Response) {
            try { $status = [int]$err.Response.StatusCode } catch {}
            try { $reader = New-Object System.IO.StreamReader($err.Response.GetResponseStream()); $respContent = $reader.ReadToEnd() } catch {}
        }
        return @{ Success = $false; Status = $status; Content = $respContent; Error = $err.Message }
    }
}

Write-Host "== Integration test for Users endpoints =="
Write-Host "Checking server at $base..."
$test = Test-NetConnection -ComputerName '127.0.0.1' -Port 5000
if (-not $test.TcpTestSucceeded) {
    Write-Host "Server not responding on 127.0.0.1:5000. Start the Flask app and re-run this script." -ForegroundColor Red
    exit 2
}

# 1) Login admin
Write-Host "\n1) Login as admin"
$loginBody = @{ email = 'admin@example.com'; password = 'AdminPass123' }
try {
    # use Invoke-RestMethod to keep cookies in $adminSession automatically
    $null = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body ($loginBody | ConvertTo-Json) -ContentType 'application/json' -SessionVariable adminSession -ErrorAction Stop
    Write-Host "Admin login: OK" -ForegroundColor Green
} catch {
    Write-Host "Admin login failed:" $_.Exception.Message -ForegroundColor Red
    exit 3
}

# 2) Create a user (use unique email per run to avoid duplicate email conflicts)
Write-Host "\n2) Create a test user as admin"
$ts = Get-Date -Format "yyyyMMddHHmmss"
$email = "juan_$ts@example.com"
$createBody = @{ nombre='Juan'; apellido='Perez'; email=$email; password='Secret123' }
$res = Send-Request -Method Post -Uri "$base/users" -Body $createBody -WebSession $adminSession
if ($res.Success -and $res.Status -eq 201) {
    $created = $res.Parsed
    $userId = $created.id
    Write-Host "User created: $($created.email) id=$userId" -ForegroundColor Green
} else {
    Write-Host "Create user failed: status=$($res.Status) error=$($res.Error) content=$($res.Content)" -ForegroundColor Red
    exit 4
}

# 3) List users
Write-Host "\n3) List users (admin)"
$res = Send-Request -Method Get -Uri "$base/users?page=1&per_page=10" -WebSession $adminSession
if ($res.Success -and $res.Status -eq 200) {
    Write-Host "List users OK. Items count: $($res.Parsed.items.Count)"
} else {
    Write-Host "List users failed: status=$($res.Status) content=$($res.Content)" -ForegroundColor Red
    exit 5
}

# 4) Login as created user
Write-Host "\n4) Login as the created user"
try {
    $null = Invoke-RestMethod -Uri "$base/auth/login" -Method Post -Body ((@{ email=$createBody.email; password=$createBody.password } ) | ConvertTo-Json) -ContentType 'application/json' -SessionVariable userSession -ErrorAction Stop
    Write-Host "User login: OK" -ForegroundColor Green
} catch {
    Write-Host "User login failed:" $_.Exception.Message -ForegroundColor Red
    exit 6
}

# 5) User updates own nombre (allowed)
Write-Host "\n5) User updates own nombre (PATCH)"
$patchBody = @{ nombre='Juanito' }
$res = Send-Request -Method Patch -Uri "$base/users/$userId" -Body $patchBody -WebSession $userSession
if ($res.Success -and $res.Status -eq 200) {
    Write-Host "User patch self OK. New nombre: $($res.Parsed.nombre)" -ForegroundColor Green
} else {
    Write-Host "User patch self failed: status=$($res.Status) content=$($res.Content)" -ForegroundColor Red
    exit 7
}

# 6) User tries to change role (forbidden)
Write-Host "\n6) User tries forbidden role change (should be forbidden)"
$badPatch = @{ role='ADMIN' }
$res = Send-Request -Method Patch -Uri "$base/users/$userId" -Body $badPatch -WebSession $userSession
if (-not $res.Success -and ($res.Status -eq 403 -or $res.Status -eq 401)) {
    Write-Host "Forbidden as expected: status=$($res.Status)" -ForegroundColor Yellow
} else {
    Write-Host "Unexpected result for forbidden role change: success=$($res.Success) status=$($res.Status) content=$($res.Content)" -ForegroundColor Red
    exit 8
}

# 7) Admin changes role to ADMIN (allowed)
Write-Host "\n7) Admin changes role of user to ADMIN"
$rolePatch = @{ role='ADMIN' }
$res = Send-Request -Method Patch -Uri "$base/users/$userId" -Body $rolePatch -WebSession $adminSession
if ($res.Success -and $res.Status -eq 200) {
    Write-Host "Admin changed role OK. New role: $($res.Parsed.role)" -ForegroundColor Green
} else {
    Write-Host "Admin role change failed: status=$($res.Status) content=$($res.Content)" -ForegroundColor Red
    exit 9
}

# 8) Admin soft-delete user
Write-Host "\n8) Admin deletes (soft-delete) the user"
$res = Send-Request -Method Delete -Uri "$base/users/$userId" -WebSession $adminSession
if ($res.Success -and $res.Status -eq 204) {
    Write-Host "Delete returned 204 No Content (OK)" -ForegroundColor Green
} elseif (-not $res.Success -and $res.Status -eq 204) {
    # sometimes Invoke-WebRequest in catch returns Status 204 in Status property
    Write-Host "Delete seems OK (status 204)." -ForegroundColor Green
} else {
    Write-Host "Delete failed: status=$($res.Status) content=$($res.Content)" -ForegroundColor Red
    exit 10
}

# 9) Confirm user not listed when is_active=true
Write-Host "\n9) Verify user not listed when filtering active users"
$res = Send-Request -Method Get -Uri "$base/users?is_active=true" -WebSession $adminSession
$found = $false
if ($res.Success -and $res.Status -eq 200) {
    foreach ($item in $res.Parsed.items) {
        if ($item.email -eq $createBody.email) { $found = $true; break }
    }
    if (-not $found) { Write-Host "User correctly absent from active list." -ForegroundColor Green } else { Write-Host "User still present in active list (unexpected)." -ForegroundColor Red; exit 11 }
} else {
    Write-Host "Failed to fetch active users: status=$($res.Status) content=$($res.Content)" -ForegroundColor Red
    exit 12
}

Write-Host "\n== Integration test completed successfully ==" -ForegroundColor Green
exit 0
