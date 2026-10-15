#!/usr/bin/env bash
# scripts/start-vm.sh — bootstrap и запуск VM стенда k3s (ТЗ, этап 5).
# 1) проверяет зависимости (qemu-system-x86_64, qemu-img, curl);
# 2) при отсутствии скачивает cloud-образ noble-server-cloudimg-amd64.img
#    и сверяет его с официальным SHA256SUMS;
# 3) при отсутствии диска создаёт overlay qcow2 (50 GiB) поверх cloud-образа;
# 4) проверяет наличие cloud-init seed.iso (NoCloud: meta-data + user-data);
# 5) запускает VM: 2 vCPU / 4096 MiB, KVM, -nographic, пробросы 2222→22 и
#    6443→6443. Все файлы остаются в VM_DIR (образы на диске, не в git).
# --check: пройти все проверки и выйти, не запуская qemu.
# --tmux:  запустить VM в фоновой сессии tmux (переживает закрытие терминала);
#          возврат из сессии — Ctrl+B, затем D; повторный запуск — подключение.
set -euo pipefail

CHECK_ONLY=0
USE_TMUX=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --tmux)  USE_TMUX=1 ;;
    *) echo "usage: start-vm.sh [--check] [--tmux]" >&2; exit 2 ;;
  esac
done

DEFAULT_DIR="/mnt/B4A692EBA692AD7C/vm/k3s-vm"

if [[ -z "${VM_DIR:-}" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "[start-vm] Каталог VM [Enter = $DEFAULT_DIR]: " VM_DIR
    VM_DIR="${VM_DIR:-$DEFAULT_DIR}"
  else
    VM_DIR="$DEFAULT_DIR"
  fi
fi
IMG_NAME="noble-server-cloudimg-amd64.img"
IMG_URL="https://cloud-images.ubuntu.com/noble/current/${IMG_NAME}"
SUMS_URL="https://cloud-images.ubuntu.com/noble/current/SHA256SUMS"
DISK="$VM_DIR/k3s-vm.qcow2"
SEED="$VM_DIR/seed.iso"

echo "[start-vm] VM_DIR=$VM_DIR"

# 1. зависимости
for bin in qemu-system-x86_64 qemu-img curl; do
  command -v "$bin" >/dev/null || {
    echo "[start-vm] ОШИБКА: нет $bin" >&2; exit 1; }
done

mkdir -p "$VM_DIR"

# 2. cloud-образ + SHA256SUMS (пара скачивается вместе и сверяется вместе)
if [[ ! -f "$VM_DIR/$IMG_NAME" || ! -f "$VM_DIR/SHA256SUMS" ]]; then
  echo "[start-vm] скачиваю cloud-образ и SHA256SUMS"
  curl -fSL -o "$VM_DIR/$IMG_NAME" "$IMG_URL"
  curl -fSL -o "$VM_DIR/SHA256SUMS" "$SUMS_URL"
fi
echo "[start-vm] сверяю SHA-256 cloud-образа"
if ! ( cd "$VM_DIR" && grep " \*$IMG_NAME\$" SHA256SUMS | sha256sum -c - ); then
  echo "[start-vm] ОШИБКА: хеш не сошёлся." >&2
  echo "[start-vm] upstream обновил 'current' или файлы из разных скачиваний;" >&2
  echo "[start-vm] удали $VM_DIR/$IMG_NAME и повтори (скачается свежая пара)." >&2
  exit 1
fi

# 3. overlay-диск поверх cloud-образа
if [[ ! -f "$DISK" ]]; then
  echo "[start-vm] создаю overlay $DISK (50G) поверх $IMG_NAME"
  qemu-img create -f qcow2 -b "$VM_DIR/$IMG_NAME" -F qcow2 "$DISK" 50G
else
  echo "[start-vm] диск уже есть: $DISK"
fi

# 4. cloud-init seed
if [[ ! -f "$SEED" ]]; then
  echo "[start-vm] ОШИБКА: нет $SEED (NoCloud: meta-data + user-data)" >&2
  echo "[start-vm] собери: cloud-localds $SEED user-data meta-data" >&2
  exit 1
fi

if (( CHECK_ONLY )); then
  echo "[start-vm] check ok: зависимости, образ (sha256), overlay, seed.iso"
  exit 0
fi

# запуск в tmux (флаг --tmux): внутри tmux'а просто идём дальше к qemu
if (( USE_TMUX )) && [[ -z "${TMUX:-}" ]]; then
  command -v tmux >/dev/null || {
    echo "[start-vm] ОШИБКА: нет tmux (sudo apt install tmux)" >&2; exit 1; }
  SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  if tmux has-session -t k3s-vm 2>/dev/null; then
    echo "[start-vm] сессия k3s-vm уже есть — подключаюсь"
    exec tmux attach -t k3s-vm
  fi
  echo "[start-vm] VM стартует в сессии tmux 'k3s-vm' (отвязка: Ctrl+B, D)"
  tmux new -d -s k3s-vm "VM_DIR='$VM_DIR' '$SELF'"
  exec tmux attach -t k3s-vm
fi

# 5. запуск (флаги — как в профиле этапа 5; консоль в foreground, запускать в tmux)
exec qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 2 -m 4096 \
  -name k3s-vm \
  -drive file="$DISK",if=virtio,format=qcow2,file.locking=off \
  -drive file="$SEED",if=virtio,format=raw,readonly=on \
  -netdev user,id=net0,hostfwd=tcp::2222-:22,hostfwd=tcp::6443-:6443 \
  -device virtio-net-pci,netdev=net0 \
  -nographic
