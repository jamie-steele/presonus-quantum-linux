-- Keep the proven 128-frame Quantum 2626 hardware period while providing
-- four periods of buffering for the shared UCM playback and capture nodes.
table.insert(alsa_monitor.rules, {
  matches = {
    {
      {
        "node.name",
        "matches",
        "alsa_output.*.HiFi__quantum2626_stereo_out_*",
      },
    },
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
