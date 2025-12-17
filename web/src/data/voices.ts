export enum VoiceId {
  ARA = "Ara",
  EVE = "Eve",
  REX = "Rex",
  ANI = "Ani",
  MIKA = "Mika",
  VALENTINE = "Valentine",
  GORK = "Gork",
  LEO = "Leo",
  SAL = "Sal",
}

export interface Voice {
  id: VoiceId;
  name: string;
  characteristic: string;
}

export const voicesData: Record<VoiceId, Voice> = {
  [VoiceId.ARA]: { id: VoiceId.ARA, name: "Ara", characteristic: "" },
  [VoiceId.EVE]: { id: VoiceId.EVE, name: "Eve", characteristic: "" },
  [VoiceId.REX]: { id: VoiceId.REX, name: "Rex", characteristic: "" },
  [VoiceId.ANI]: { id: VoiceId.ANI, name: "Ani", characteristic: "" },
  [VoiceId.MIKA]: { id: VoiceId.MIKA, name: "Mika", characteristic: "" },
  [VoiceId.VALENTINE]: { id: VoiceId.VALENTINE, name: "Valentine", characteristic: "" },
  [VoiceId.GORK]: { id: VoiceId.GORK, name: "Gork", characteristic: "" },
  [VoiceId.LEO]: { id: VoiceId.LEO, name: "Leo", characteristic: "" },
  [VoiceId.SAL]: { id: VoiceId.SAL, name: "Sal", characteristic: "" },
};

export const voices: Voice[] = Object.values(voicesData);
