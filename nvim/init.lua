-- bootstrap lazy.nvim, LazyVim and your plugins
require("config.lazy")
require("config.lazy") -- Plugin management
require("config.git") -- Git settings
require("config.copilot") -- Copilot settings

vim.opt.clipboard = "unnamedplus"
