package com.mobilemorph.agent.telemetry

import io.opentelemetry.api.GlobalOpenTelemetry
import io.opentelemetry.api.common.Attributes
import io.opentelemetry.api.common.AttributeKey.stringKey
import io.opentelemetry.api.trace.SpanKind

object Telemetry {
    private val tracer = GlobalOpenTelemetry.getTracer("com.mobilemorph.security")

    fun securityEvent(name: String, attrs: Map<String, String>) {
        val span = tracer.spanBuilder(name)
            .setSpanKind(SpanKind.INTERNAL)
            .startSpan()
        attrs.forEach { (k, v) -> span.setAttribute(stringKey(k), v) }
        span.end()
    }
}
