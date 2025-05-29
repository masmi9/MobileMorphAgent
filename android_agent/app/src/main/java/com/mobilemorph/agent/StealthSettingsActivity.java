package com.mobilemorph.agent;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.Toast;

public class StealthSettingsActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_stealth_settings);

        CheckBox stealthToggle = findViewById(R.id.stealthToggle);

        SharedPreferences prefs = getSharedPreferences("agent", MODE_PRIVATE);
        boolean stealth = prefs.getBoolean("stealth_mode", false);
        stealthToggle.setChecked(stealth);

        stealthToggle.setOnCheckedChangeListener((buttonView, isChecked) -> {
            prefs.edit().putBoolean("stealth_mode", isChecked).apply();
            Toast.makeText(this, "Stealth mode " + (isChecked ? "enabled" : "disabled"), Toast.LENGTH_SHORT).show();
        });
    }
}
