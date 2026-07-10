import React from "react";
import SignupForm from "../../../components/auth/SignupForm";

export const metadata = {
  title: "Create Account | AquaSense",
  description:
    "Create a new account on AquaSense smart water monitoring system.",
};

export default function SignupPage() {
  return (
    <div>
      <SignupForm />
    </div>
  );
}
