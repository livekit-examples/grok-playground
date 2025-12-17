export enum VoiceId {
  AVA = "Ava",
}

export interface Voice {
  id: VoiceId;
  name: string;
  characteristic: string;
}

export const voicesData: Record<VoiceId, Voice> = {
  [VoiceId.AVA]: {
    id: VoiceId.AVA,
    name: "Ava",
    characteristic: "Default",
  },
};

export const voices: Voice[] = Object.values(voicesData);
