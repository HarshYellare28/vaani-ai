// AudioWorklet processor — runs on the dedicated audio thread and forwards
// mic samples (channel 0) to the main thread. Replaces the deprecated
// ScriptProcessorNode. One quantum is 128 frames, so tail loss on stop is
// negligible (~3 ms).

class CaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length) {
      // slice(0) copies the frame out of the reused worklet buffer before
      // it's posted (structured-cloned) to the main thread.
      this.port.postMessage(input[0].slice(0));
    }
    return true; // keep the processor alive
  }
}

registerProcessor("capture-processor", CaptureProcessor);
