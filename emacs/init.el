;; PACKAGE MANAGEMENT
(require 'package)

(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(add-to-list 'package-archives '("org" . "https://orgmode.org/elpa/") t)
(add-to-list 'package-archives '("elpa" . "https://elpa.gnu.org/packages/") t)

(package-initialize)

;; Refresh package list if it's the first time running
(unless package-archive-contents
  (package-refresh-contents))

;; Install 'use-package' if not present.
;; This tool makes future plugin configuration much easier.
(unless (package-installed-p 'use-package)
  (package-install 'use-package))

(require 'use-package)
;; Ensure that packages are automatically downloaded if missing
(setq use-package-always-ensure t)

;; THEME
(use-package doom-themes
  :config
  (setq doom-themes-enable-bold t
        doom-themes-enable-italic t)
 
  (load-theme 'doom-dracula t)
  
  (doom-themes-org-config))

;; UI
(setq inhibit-startup-message t)   	; Disable the initial startup logo
(global-display-line-numbers-mode t) 	; Enable line numbers globally
(show-paren-mode 1)                	; Highlight matching parentheses

;; Use 'y' and 'n' instead of typing 'yes' and 'no'
(defalias 'yes-or-no-p 'y-or-n-p)

;; BACKUPS
;; Emacs creates backup files ending in ~.
;; This moves them to a temporary folder to keep your directories clean.
(setq backup-directory-alist `(("." . ,(expand-file-name "tmp/backups/" user-emacs-directory))))
(setq auto-save-list-file-prefix (expand-file-name "tmp/auto-saves/sessions/" user-emacs-directory))