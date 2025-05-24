package com.mobilemorph.agent.jobs;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.mobilemorph.agent.util.ShellExecutor;

public class AgentWorker extends Worker {
    public AgentWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        ShellExecutor.execute("whoami");  // Replace with your agent logic
        return Result.success();
    }
}
