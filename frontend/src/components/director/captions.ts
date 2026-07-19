interface ITimedCaptionWord {
  text: string;
  startsAt: number;
  endsAt: number;
}

const lexicalLength = (word: string): number => {
  return Array.from(word.replace(/[^\p{L}\p{N}]/gu, '')).length;
};

const timingWeight = (word: string): number => {
  const lengthWeight = Math.max(0.72, Math.min(1.7, 0.45 + lexicalLength(word) * 0.12));

  if (/[.!?]$/u.test(word)) {
    return lengthWeight + 0.68;
  }
  if (/[;:—–]$/u.test(word)) {
    return lengthWeight + 0.48;
  }
  if (/[,…]$/u.test(word)) {
    return lengthWeight + 0.3;
  }
  return lengthWeight;
};

const buildTimedCaptionWords = (text: string, durationSeconds: number): ITimedCaptionWord[] => {
  const words = text.trim().split(/\s+/u).filter(Boolean);

  if (words.length === 0 || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    return [];
  }

  const weights = words.map(timingWeight);
  const totalWeight = weights.reduce((total, weight) => total + weight, 0);
  const leadIn = Math.min(0.12, durationSeconds * 0.025);
  const tail = Math.min(0.18, durationSeconds * 0.04);
  const spokenDuration = Math.max(0.05, durationSeconds - leadIn - tail);
  let consumedWeight = 0;

  return words.map((word, index) => {
    const startsAt = leadIn + (consumedWeight / totalWeight) * spokenDuration;
    consumedWeight += weights[index];
    const endsAt = leadIn + (consumedWeight / totalWeight) * spokenDuration;
    return { text: word, startsAt, endsAt };
  });
};

const captionWordIndexAt = (words: ITimedCaptionWord[], currentTime: number): number => {
  if (words.length === 0) {
    return -1;
  }

  const index = words.findIndex((word) => currentTime < word.endsAt);
  return index === -1 ? words.length - 1 : index;
};

export { buildTimedCaptionWords, captionWordIndexAt };
