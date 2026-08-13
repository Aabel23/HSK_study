/**
 * Convert a recorded clip to 16 kHz mono WAV, base64 encoded.
 *
 * MediaRecorder gives us WebM/Opus in Chrome and Ogg/Opus in Firefox, and the
 * Gemini API accepts neither reliably. WAV is accepted everywhere, and the
 * browser can already decode whatever it just recorded, so the conversion is
 * local: decode → downmix to mono → resample → write a PCM WAV header.
 *
 * 16 kHz mono is what speech models want anyway, and it keeps a two-minute
 * answer near 3.8 MB before base64 rather than an order of magnitude more.
 */

const TARGET_SAMPLE_RATE = 16000;

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeText = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index));
    }
  };

  writeText(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeText(8, "WAVE");
  writeText(12, "fmt ");
  view.setUint32(16, 16, true); // PCM header size
  view.setUint16(20, 1, true); // format: PCM
  view.setUint16(22, 1, true); // channels: mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeText(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1) {
    // Clamp before scaling, otherwise a loud passage wraps around into noise.
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }
  return buffer;
}

function toBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  // Chunked so a long clip cannot blow the argument limit of String.fromCharCode.
  const chunk = 0x8000;
  for (let index = 0; index < bytes.length; index += chunk) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunk));
  }
  return btoa(binary);
}

export async function blobToWavBase64(blob: Blob): Promise<string> {
  const arrayBuffer = await blob.arrayBuffer();
  const AudioContextClass =
    window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
  const decodeContext = new AudioContextClass();
  let decoded: AudioBuffer;
  try {
    decoded = await decodeContext.decodeAudioData(arrayBuffer.slice(0));
  } finally {
    void decodeContext.close();
  }

  const sampleRate = Math.min(TARGET_SAMPLE_RATE, decoded.sampleRate);
  const frames = Math.ceil((decoded.duration * sampleRate) || 1);
  const offline = new OfflineAudioContext(1, frames, sampleRate);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const rendered = await offline.startRendering();

  return toBase64(encodeWav(rendered.getChannelData(0), sampleRate));
}
