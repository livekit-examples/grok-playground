export enum VoiceId {
  ARA = "Ara",
  REX = "Rex",
  SAL = "Sal",
  EVE = "Eve",
  LEO = "Leo",
  // Voices not yet available - uncomment when supported:
  // ANI = "Ani",
  // MIKA = "Mika",
  // VALENTINE = "Valentine",
  // GORK = "Gork",
}

export interface Voice {
  id: VoiceId;
  name: string;
  type: string;
  tone: string;
  description: string;
}

export const voicesData: Record<VoiceId, Voice> = {
  [VoiceId.ARA]: {
    id: VoiceId.ARA,
    name: "Ara",
    type: "Female",
    tone: "Warm, friendly",
    description: "Default voice, balanced and conversational",
  },
  [VoiceId.REX]: {
    id: VoiceId.REX,
    name: "Rex",
    type: "Male",
    tone: "Confident, clear",
    description: "Professional and articulate, ideal for business applications",
  },
  [VoiceId.SAL]: {
    id: VoiceId.SAL,
    name: "Sal",
    type: "Neutral",
    tone: "Smooth, balanced",
    description: "Versatile voice suitable for various contexts",
  },
  [VoiceId.EVE]: {
    id: VoiceId.EVE,
    name: "Eve",
    type: "Female",
    tone: "Energetic, upbeat",
    description: "Engaging and enthusiastic, great for interactive experiences",
  },
  [VoiceId.LEO]: {
    id: VoiceId.LEO,
    name: "Leo",
    type: "Male",
    tone: "Authoritative, strong",
    description: "Decisive and commanding, suitable for instructional content",
  },
};

export const voices: Voice[] = Object.values(voicesData);
