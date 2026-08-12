<#
.SYNOPSIS
    Create a self-signed code-signing certificate and trust it on THIS computer.

.DESCRIPTION
    Use this when you just want ChineseStudy.exe to stop warning on your own
    machine (or on a small set of machines you administer).

    What it does and does not do:
      * It DOES remove the "unknown publisher" warning on machines where this
        certificate has been installed into Trusted Root + Trusted Publishers.
      * It does NOT help on anyone else's computer. A self-signed certificate
        carries no third-party trust, so SmartScreen will still warn everywhere
        else. Only an OV or EV certificate from a commercial CA fixes that for
        the general public -- see docs/WINDOWS_TRUST.md.

    Installing a root certificate is a real change to your machine's trust
    store. Only run this if you understand and accept that.

.PARAMETER Subject
    The publisher name shown to users. Defaults to "Chinese Study".

.PARAMETER Years
    Certificate lifetime in years. Defaults to 5.

.PARAMETER Trust
    Also install the certificate into Trusted Root and Trusted Publishers for
    the current user. Without this the certificate is created but not trusted.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\make_selfsigned_cert.ps1 -Trust
#>

[CmdletBinding()]
param(
    [string]$Subject = "Chinese Study",
    [int]$Years = 5,
    [switch]$Trust
)

$ErrorActionPreference = "Stop"

Write-Host "Creating a self-signed code-signing certificate for '$Subject'..."

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=$Subject, O=$Subject, C=VN" `
    -KeyUsage DigitalSignature `
    -KeyAlgorithm RSA `
    -KeyLength 3072 `
    -HashAlgorithm SHA256 `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears($Years)

Write-Host "  Thumbprint: $($cert.Thumbprint)"

if ($Trust) {
    Write-Host "Installing the certificate into the local trust stores..."
    foreach ($store in @("Root", "TrustedPublisher")) {
        $target = New-Object System.Security.Cryptography.X509Certificates.X509Store($store, "CurrentUser")
        $target.Open("ReadWrite")
        $target.Add($cert)
        $target.Close()
        Write-Host "  Added to Cert:\CurrentUser\$store"
    }
    Write-Host "This computer will now accept executables signed with this certificate."
} else {
    Write-Host "Certificate created but NOT trusted. Re-run with -Trust to install it."
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  `$env:CHINESE_STUDY_CERT_SUBJECT = '$Subject'"
Write-Host "  python scripts\build_exe.py --sign"
Write-Host ""
Write-Host "Reminder: this only silences the warning on machines that trust this" -ForegroundColor Yellow
Write-Host "certificate. Other people will still see SmartScreen." -ForegroundColor Yellow
