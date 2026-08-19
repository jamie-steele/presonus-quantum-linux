-- Keep the proven 128-frame Quantum 2626 hardware period while providing
-- four periods of buffering for the shared UCM playback nodes. Retain one
-- two periods of playback headroom for the dshare pointer-timing path.
table.insert(alsa_monitor.rules, {
  matches = {
    {
      {
        "node.name",
        "matches",
        "alsa_output.*.HiFi__quantum2626_stereo_out_*",
      },
    },
  },
  apply_properties = {
    ["api.alsa.period-size"] = 128,
    ["api.alsa.period-num"] = 4,
    ["api.alsa.headroom"] = 256,
  },
})

-- Capture keeps the same period geometry without the playback diagnostic's
-- additional headroom.
table.insert(alsa_monitor.rules, {
  matches = {
    {
      {
        "node.name",
        "matches",
        "alsa_input.*.HiFi__quantum2626_mono_in_*",
      },
    },
  },
  apply_properties = {
    ["api.alsa.period-size"] = 128,
    ["api.alsa.period-num"] = 4,
  },
})
