package com.mobilemorph.agent.receiver;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import com.mobilemorph.agent.jobs.AgentWorker;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Log.d("BootReceiver", "Boot detected, starting AgentWorker...");
            WorkManager.getInstance(context).enqueue(new OneTimeWorkRequest.Builder(AgentWorker.class).build());
        }
    }
}
