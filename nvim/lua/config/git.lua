require("gitsigns").setup({
  signs = {
    add = { text = "+" },
    change = { text = "~" },
    delete = { text = "_" },
    topdelete = { text = "‾" },
    changedelete = { text = "~" },
  },
  keymaps = {
    noremap = true,
    buffer = true,
    ["n ]c"] = { expr = true, "&diff ? ']c' : '<cmd>Gitsigns next_hunk<CR>'" },
    ["n [c"] = { expr = true, "&diff ? '[c' : '<cmd>Gitsigns prev_hunk<CR>'" },
    ["n <leader>gs"] = "<cmd>Gitsigns stage_hunk<CR>",
    ["n <leader>gu"] = "<cmd>Gitsigns undo_stage_hunk<CR>",
    ["n <leader>gr"] = "<cmd>Gitsigns reset_hunk<CR>",
    ["n <leader>gp"] = "<cmd>Gitsigns preview_hunk<CR>",
  },
})
