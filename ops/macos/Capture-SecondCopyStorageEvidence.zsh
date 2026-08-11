#!/bin/zsh
set -euo pipefail
umask 077

SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/Common.zsh"

root="${INTERNAL_EXAM_ROOT:-${HOME:?}/Library/Application Support/InternalExam}"
while (( $# > 0 )); do
  case "$1" in
    --root) (( $# >= 2 )) || macos_die "--root requires a path"; root="$2"; shift 2 ;;
    -h|--help) print -r -- "usage: $0 [--root ABSOLUTE_ROOT]"; exit 0 ;;
    *) macos_die "unknown argument: $1"; exit 1 ;;
  esac
done

macos_assert_macos
macos_assert_outside_worktree "$root" >/dev/null
macos_layout "$root"
macos_assert_protected_configuration "$root"
macos_require_command df
macos_require_command diskutil
macos_require_command plutil
second_copy_path="$(macos_formal_value SECOND_COPY_PATH)"
second_copy_path="$(macos_resolve_path "$second_copy_path")"
macos_assert_outside_worktree "$second_copy_path" >/dev/null
[[ -d "$second_copy_path" ]] || macos_die "configured second-copy path is not mounted"
[[ -f "$second_copy_path/.internal-exam-encrypted-storage" ]] || macos_die "encrypted second-copy marker is missing"
[[ -w "$second_copy_path" ]] || macos_die "second-copy path is not writable"

disk_info="$(macos_mktemp internal-exam-second-copy-disk-info.XXXXXX)"
formal_disk_info="$(macos_mktemp internal-exam-formal-disk-info.XXXXXX)"
cleanup_capture() { rm -f -- "$disk_info" "$formal_disk_info"; }
trap cleanup_capture EXIT
diskutil info -plist "$second_copy_path" > "$disk_info" 2>/dev/null || macos_die "diskutil cannot inspect second-copy storage"
diskutil info -plist "$MACOS_LAYOUT_ROOT" > "$formal_disk_info" 2>/dev/null || macos_die "diskutil cannot inspect formal storage"
mount_point="$(plutil -extract MountPoint raw -o - -- "$disk_info" 2>/dev/null || true)"
encrypted="$(plutil -extract Encryption raw -o - -- "$disk_info" 2>/dev/null || true)"
filevault="$(plutil -extract FileVault raw -o - -- "$disk_info" 2>/dev/null || true)"
writable_volume="$(plutil -extract WritableVolume raw -o - -- "$disk_info" 2>/dev/null || true)"
device_id="$(plutil -extract DeviceIdentifier raw -o - -- "$disk_info" 2>/dev/null || true)"
whole_device_id="$(plutil -extract ParentWholeDisk raw -o - -- "$disk_info" 2>/dev/null || true)"
formal_whole_device_id="$(plutil -extract ParentWholeDisk raw -o - -- "$formal_disk_info" 2>/dev/null || true)"
[[ "$mount_point" == "$second_copy_path" && ( "$encrypted" == true || "$filevault" == true ) && "$writable_volume" == true ]] || macos_die "second-copy disk is not mounted encrypted and writable"
[[ "$device_id" =~ '^disk[0-9]+(s[0-9]+)+$' && "$whole_device_id" =~ '^disk[0-9]+$' && "$formal_whole_device_id" =~ '^disk[0-9]+$' ]] || macos_die "diskutil did not provide stable device identities"
[[ "$whole_device_id" != "$formal_whole_device_id" ]] || macos_die "second-copy storage must be on a distinct physical disk"
live_device="$(df -P "$second_copy_path" | tail -n 1 | awk '{print $1}')"
[[ "$live_device" == /dev/* ]] || macos_die "df did not report a mounted second-copy device"

host_id="unknown"
if [[ -f "$MACOS_LAYOUT_STATE/host-identity.json" && -f "$MACOS_LAYOUT_STATE/host-identity.json.sha256" ]]; then
  macos_check_checksum "$MACOS_LAYOUT_STATE/host-identity.json"
  host_id="$(macos_json_get "$MACOS_LAYOUT_STATE/host-identity.json" hostId 2>/dev/null || true)"
fi
evidence_path="$MACOS_LAYOUT_EVIDENCE/second-copy-storage.json"
macos_write_atomic "$evidence_path" "{\"schemaVersion\":1,\"kind\":\"second-copy-storage\",\"status\":\"passed\",\"hostId\":\"$(macos_json_escape "$host_id")\",\"path\":\"$(macos_json_escape "$second_copy_path")\",\"mountPoint\":\"$(macos_json_escape "$mount_point")\",\"mounted\":true,\"writable\":true,\"encrypted\":true,\"deviceId\":\"$(macos_json_escape "/dev/$device_id")\",\"wholeDeviceId\":\"$(macos_json_escape "/dev/$whole_device_id")\",\"formalWholeDeviceId\":\"$(macos_json_escape "/dev/$formal_whole_device_id")\",\"liveDevice\":\"$(macos_json_escape "$live_device")\",\"distinctPhysicalDevice\":true,\"markerPresent\":true,\"checkedAt\":\"$(macos_now_iso)\",\"secrets\":\"excluded\"}"
macos_checksummed_json "$evidence_path"
macos_secure_path "$evidence_path"
macos_log "second_copy_storage_evidence status=passed path=${second_copy_path:t} device=/dev/$whole_device_id"
