local app_shortcuts = {
  {'1', 'iTerm'},
  {'2', 'Visual Studio Code'},
  {'3', 'Google Chrome'},
  {'4', 'Obsidian'},
  {'5', 'Antigravity IDE'},
  {'6', 'Codex'},
  {'7', 'Activity Monitor'},
  {'8', 'System Settings'},
}

for _, shortcut in ipairs(app_shortcuts) do
  local key, appName = table.unpack(shortcut)
  hs.hotkey.bind({"cmd"}, key, function()
    hs.application.launchOrFocus(appName)
  end)
end