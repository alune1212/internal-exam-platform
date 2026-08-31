#!/bin/zsh
set -euo pipefail
setopt no_nomatch
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

release_path=""
private_key=""
public_key=""
fingerprint_file=""
root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --release-path|--release) (( $# >= 2 )) || macos_die "$1 requires a path"; release_path="$2"; shift 2 ;;
    --private-key) (( $# >= 2 )) || macos_die "--private-key requires a path"; private_key="$2"; shift 2 ;;
    --public-key|--signing-public-key) (( $# >= 2 )) || macos_die "$1 requires a path"; public_key="$2"; shift 2 ;;
    --fingerprint|--signing-fingerprint) (( $# >= 2 )) || macos_die "$1 requires a path"; fingerprint_file="$2"; shift 2 ;;
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help)
      print -r -- "usage: $0 --release-path SEALED_RELEASE --private-key OFFLINE_RSA3072_PRIVATE_KEY [--public-key PUBLIC_KEY --fingerprint FINGERPRINT_FILE] [--root ROOT]"
      exit 0
      ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
[[ -n "$release_path" && -n "$private_key" ]] || macos_die "release and offline private key are required"
[[ ! -L "$release_path" ]] || macos_die "release directory must not be a symlink"
[[ ! -L "$private_key" ]] || macos_die "offline private key must not be a symlink"
release_path="$(macos_resolve_path "$release_path")"
private_key="$(macos_resolve_path "$private_key")"
[[ -d "$release_path" && ! -L "$release_path" ]] || macos_die "release directory is missing or a symlink"
[[ -f "$private_key" && ! -L "$private_key" ]] || macos_die "offline private key is missing or a symlink"
macos_secure_path "$private_key"
macos_require_command openssl

private_details="$(openssl rsa -in "$private_key" -text -noout 2>/dev/null)" || macos_die "offline signing key must be an RSA private key"
[[ "$private_details" == *"Private-Key: (3072 bit"* ]] || macos_die "offline signing key must be RSA-3072"

work="$(mktemp -d -t internal-exam-release-sign-XXXXXX)"
chmod 700 "$work"
cleanup_signing() { [[ -z "${work:-}" ]] || rm -R -- "$work"; }
trap cleanup_signing EXIT

derived_public_key="$work/derived-public-key.pem"
touch "$derived_public_key"
chmod 600 "$derived_public_key"
openssl pkey -in "$private_key" -pubout -out "$derived_public_key" >/dev/null 2>&1 || macos_die "unable to derive the offline signing public key"
derived_fingerprint="$(macos_release_signing_key_fingerprint "$derived_public_key")"

if [[ -n "$public_key" ]]; then
  [[ ! -L "$public_key" ]] || macos_die "signing public key must not be a symlink"
  public_key="$(macos_resolve_path "$public_key")"
  macos_secure_path "$public_key"
  macos_assert_rsa3072_public_key "$public_key"
  public_fingerprint="$(macos_release_signing_key_fingerprint "$public_key")"
  [[ "$public_fingerprint" == "$derived_fingerprint" ]] || macos_die "public key does not match the offline private key"
else
  public_key="$derived_public_key"
  public_fingerprint="$derived_fingerprint"
fi

if [[ -n "$fingerprint_file" ]]; then
  [[ ! -L "$fingerprint_file" ]] || macos_die "signing fingerprint must not be a symlink"
  fingerprint_file="$(macos_resolve_path "$fingerprint_file")"
  macos_secure_path "$fingerprint_file"
  expected_fingerprint="$(tr -d '[:space:]' < "$fingerprint_file")"
  [[ "$expected_fingerprint" == "${public_fingerprint:l}" ]] || macos_die "external signing fingerprint does not match the offline public key"
else
  fingerprint_file="$work/release-signing-public-key.fingerprint"
  print -r -- "$public_fingerprint" > "$fingerprint_file"
  chmod 600 "$fingerprint_file"
fi

manifest="$release_path/release-manifest.json"
checksums="$release_path/SHA256SUMS"
[[ -f "$manifest" && ! -L "$manifest" && -f "$checksums" && ! -L "$checksums" ]] || macos_die "release manifest or SHA256SUMS is missing or a symlink"

# Validate the sealed content before changing its metadata.  This mode is only
# for the offline signer; every install/start/promotion/rollback path invokes
# Test-ReleaseBundle without this flag.
"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --root "$root" \
  --signing-public-key "$public_key" --signing-fingerprint "$fingerprint_file" \
  --allow-signature-missing >/dev/null

temporary_manifest="$work/release-manifest.json"
cp -p -- "$manifest" "$temporary_manifest"
chmod 600 "$temporary_manifest"
plutil -remove releaseSignature -- "$temporary_manifest" >/dev/null 2>&1 || true
signature_metadata="{\"schemaVersion\":1,\"algorithm\":\"RSA-SHA256\",\"keyFingerprint\":\"$public_fingerprint\",\"signedFiles\":[\"release-manifest.json\",\"SHA256SUMS\"],\"sidecars\":[\"release-manifest.json.sig\",\"SHA256SUMS.sig\"]}"
plutil -insert releaseSignature -json "$signature_metadata" -- "$temporary_manifest" >/dev/null 2>&1 || macos_die "unable to write release signature metadata"
plutil -convert json -o - -- "$temporary_manifest" >/dev/null 2>&1 || macos_die "release signature manifest is invalid JSON"

temporary_manifest_signature="$work/release-manifest.json.sig"
temporary_checksums_signature="$work/SHA256SUMS.sig"
# OpenSSL dgst RSA signing is the required PKCS#1 v1.5 mode here; do not
# replace it with a PSS sigopt without changing the release algorithm contract.
openssl dgst -sha256 -sign "$private_key" -out "$temporary_manifest_signature" "$temporary_manifest" >/dev/null 2>&1 || macos_die "unable to sign the release manifest"
openssl dgst -sha256 -sign "$private_key" -out "$temporary_checksums_signature" "$checksums" >/dev/null 2>&1 || macos_die "unable to sign SHA256SUMS"
[[ -s "$temporary_manifest_signature" && -s "$temporary_checksums_signature" ]] || macos_die "release signatures are empty"

mv -f -- "$temporary_manifest" "$manifest"
mv -f -- "$temporary_manifest_signature" "$release_path/$MACOS_RELEASE_MANIFEST_SIGNATURE_NAME"
mv -f -- "$temporary_checksums_signature" "$release_path/$MACOS_RELEASE_CHECKSUM_SIGNATURE_NAME"
chmod 600 "$manifest" "$release_path/$MACOS_RELEASE_MANIFEST_SIGNATURE_NAME" "$release_path/$MACOS_RELEASE_CHECKSUM_SIGNATURE_NAME"

"$SCRIPT_DIR/Test-ReleaseBundle.zsh" --release-path "$release_path" --root "$root" \
  --signing-public-key "$public_key" --signing-fingerprint "$fingerprint_file" >/dev/null
macos_log "release_signed version=$(macos_json_get "$manifest" applicationVersion) commit=$(macos_json_get "$manifest" gitCommit) algorithm=RSA-SHA256 key_fingerprint=$public_fingerprint next=Test-ReleaseBundle"
