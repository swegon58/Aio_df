"use client";

import {
  ArrowLeftIcon,
  ArrowRightIcon,
  MessageCircleQuestionMarkIcon,
  SendIcon,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { ClarificationArgs } from "@/core/messages/utils";

const SKIP_ANSWER = "No preference — please use your best judgment and proceed.";

export function ClarificationCard({
  args,
  onAnswer,
}: {
  args: ClarificationArgs;
  onAnswer: (answer: string) => void;
}) {
  const questions = args.questions;
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<(string | undefined)[]>(
    () => new Array(questions.length).fill(undefined),
  );
  const [otherText, setOtherText] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const question = questions[index];
  const isLast = index === questions.length - 1;
  const canSubmit = answers.every((a) => a !== undefined);

  if (!question) {
    return null;
  }

  const answerCurrent = (answer: string) => {
    const trimmed = answer.trim();
    if (!trimmed || submitted) {
      return;
    }
    setAnswers((prev) => {
      const next = [...prev];
      next[index] = trimmed;
      return next;
    });
    setOtherText("");
    if (!isLast) {
      setIndex((i) => i + 1);
    }
  };

  const goBack = () => {
    if (index === 0 || submitted) {
      return;
    }
    setOtherText("");
    setIndex((i) => i - 1);
  };

  const goNext = () => {
    if (isLast || submitted || answers[index] === undefined) {
      return;
    }
    setOtherText("");
    setIndex((i) => i + 1);
  };

  const submitAll = () => {
    if (!canSubmit || submitted) {
      return;
    }
    setSubmitted(true);
    const combined = questions
      .map((q, i) => `${i + 1}. ${q.question}\n${answers[i]}`)
      .join("\n\n");
    onAnswer(combined);
  };

  return (
    <Card className="w-full max-w-(--container-width-md) gap-3 py-4">
      <CardHeader className="gap-1 px-4">
        <CardTitle className="flex items-center justify-between gap-2 text-sm">
          <span className="flex items-center gap-2">
            <MessageCircleQuestionMarkIcon className="size-4" />
            Quick question
          </span>
          {questions.length > 1 && (
            <span className="text-muted-foreground text-xs font-normal">
              Question {index + 1}/{questions.length}
            </span>
          )}
        </CardTitle>
        <CardDescription className="text-foreground text-sm">
          {question.question}
        </CardDescription>
        {question.context && (
          <CardDescription className="text-xs">
            {question.context}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2 px-4">
        {question.options?.map((option) => (
          <Button
            key={option}
            className="h-auto justify-start text-wrap"
            disabled={submitted}
            onClick={() => answerCurrent(option)}
            size="sm"
            type="button"
            variant={answers[index] === option ? "default" : "outline"}
          >
            {option}
          </Button>
        ))}
        <div className="flex items-center gap-2">
          <Input
            disabled={submitted}
            onChange={(e) => setOtherText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                answerCurrent(otherText);
              }
            }}
            placeholder={
              question.options?.length
                ? "Other — type your own answer"
                : "Your answer"
            }
            value={otherText}
          />
          <Button
            disabled={submitted || !otherText.trim()}
            onClick={() => answerCurrent(otherText)}
            size="icon-sm"
            type="button"
            variant="secondary"
          >
            <SendIcon />
          </Button>
        </div>
        {answers[index] !== undefined &&
          !question.options?.includes(answers[index] ?? "") && (
            <p className="text-muted-foreground text-xs">
              Answered: {answers[index]}
            </p>
          )}
        <div className="flex items-center justify-between gap-2">
          <Button
            className="text-muted-foreground h-auto px-0"
            disabled={submitted}
            onClick={() => answerCurrent(SKIP_ANSWER)}
            size="sm"
            type="button"
            variant="link"
          >
            Skip
          </Button>
          <div className="flex items-center gap-2">
            <Button
              disabled={index === 0 || submitted}
              onClick={goBack}
              size="sm"
              type="button"
              variant="outline"
            >
              <ArrowLeftIcon />
              Back
            </Button>
            {isLast ? (
              <Button
                disabled={!canSubmit || submitted}
                onClick={submitAll}
                size="sm"
                type="button"
              >
                Submit
              </Button>
            ) : (
              <Button
                disabled={answers[index] === undefined || submitted}
                onClick={goNext}
                size="sm"
                type="button"
                variant="outline"
              >
                Next
                <ArrowRightIcon />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
