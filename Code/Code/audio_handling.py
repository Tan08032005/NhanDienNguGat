import os
import numpy as np
import av
from scipy.io import wavfile
from scipy.signal import resample_poly
class AudioFrameHandler:
    def __init__(self, wav_path: str, volume: float = 0.8, loop: bool = True):

        if not os.path.isfile(wav_path):
            raise FileNotFoundError(f"Không thấy file: {wav_path}")
            
        self.wav_path = wav_path
        self.volume = float(volume)
        self.loop = loop

        try:
            self.sound = pygame.mixer.Sound(wav_path)
            self.sound.set_volume(self.volume)

        except Exception as e:
            print(f"Lỗi khi tải file âm thanh: {e}")

        # Đọc file wav để phục vụ WebRTC audio processing
        sr, data = wavfile.read(wav_path)

        self.src_sr = int(sr)

        if np.issubdtype(data.dtype, np.integer):
            maxv = float(np.iinfo(data.dtype).max)
            data = data.astype(np.float32) / maxv
        else:
            data = data.astype(np.float32)

        if data.ndim == 1:
            data = data[:, None]

        self.src = data
        self.src_channels = self.src.shape[1]

        self.ptr = 0

        self._cache_sr = None
        self._cache_audio = None

    def _get_buffer_at_sr(self, dst_sr: int) -> np.ndarray:
        """
        Resample audio về sample rate đích.
        """

        if self._cache_sr == dst_sr and self._cache_audio is not None:
            return self._cache_audio

        g = np.gcd(self.src_sr, dst_sr)

        up = dst_sr // g
        down = self.src_sr // g

        channels = []

        for ch in range(self.src_channels):
            channels.append(
                resample_poly(
                    self.src[:, ch],
                    up,
                    down
                ).astype(np.float32)
            )

        dst = np.stack(channels, axis=1)

        self._cache_sr = dst_sr
        self._cache_audio = dst

        return dst

        """
        Phát hoặc dừng âm thanh cảnh báo.
        """

        if play_sound and self.sound and not self.is_playing:

            if self.loop:
                self.channel = self.sound.play(loops=-1)
            else:
                self.channel = self.sound.play()

            self.is_playing = True

        elif not play_sound and self.is_playing:

            if self.channel:
                self.channel.stop()

            self.is_playing = False
            self.channel = None

   
        """
        Dừng còi ngay lập tức.
        Gọi khi người dùng nhấn STOP camera.
        """

        if self.channel:
            self.channel.stop()

        self.is_playing = False
        self.channel = None
        self.ptr = 0

    def process(self, frame: av.AudioFrame, play_sound: bool) -> av.AudioFrame:


        audio = frame.to_ndarray()

        transposed_back = False

        if audio.ndim == 1:
            audio = audio[:, None]

        elif audio.shape[0] <= 8 and audio.shape[1] > 64:
            audio = audio.T
            transposed_back = True

        n_samples, n_channels = audio.shape

        dst_sr = int(frame.sample_rate)

        if not play_sound:

            audio[:] = 0

        else:

            buf = self._get_buffer_at_sr(dst_sr)

            end = self.ptr + n_samples

            if end <= buf.shape[0]:

                chunk = buf[self.ptr:end, :]
                self.ptr = end

            else:

                first = buf[self.ptr:, :]
                remain = end - buf.shape[0]

                if self.loop:

                    second = (
                        buf[:remain, :]
                        if remain > 0
                        else np.empty(
                            (0, buf.shape[1]),
                            dtype=np.float32
                        )
                    )

                    chunk = np.concatenate(
                        [first, second],
                        axis=0
                    )

                    self.ptr = remain % buf.shape[0]

                else:

                    pad = np.zeros(
                        (remain, buf.shape[1]),
                        dtype=np.float32
                    )

                    chunk = np.concatenate(
                        [first, pad],
                        axis=0
                    )

                    self.ptr = buf.shape[0]

            csrc = chunk.shape[1]

            if n_channels == csrc:

                out = chunk

            elif n_channels < csrc:

                out = chunk[:, :n_channels]

            else:

                repeat = int(np.ceil(n_channels / csrc))

                out = np.tile(
                    chunk,
                    (1, repeat)
                )[:, :n_channels]

            out = (
                out * self.volume
            ).astype(np.float32)

            if np.issubdtype(audio.dtype, np.integer):

                maxv = float(
                    np.iinfo(audio.dtype).max
                )

                audio[:] = np.clip(
                    out * maxv,
                    -maxv,
                    maxv - 1
                ).astype(audio.dtype)

            else:

                audio[:] = out.astype(audio.dtype)

        if transposed_back:
            audio = audio.T

        new_frame = av.AudioFrame.from_ndarray(
            audio,
            layout=frame.layout.name
        )

        new_frame.sample_rate = frame.sample_rate

        return new_frame